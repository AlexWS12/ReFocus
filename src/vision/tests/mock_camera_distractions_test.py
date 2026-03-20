"""
Mock camera distraction runner.

Purpose:
- Creates/uses data.db via SessionManager
- Simulates camera-driven distractions without opening the webcam
- Persists one full session row so scoring/UI can be tested quickly

Run from project root:
    python src/vision/tests/mock_camera_distractions_test.py
"""

import os
import sys
import time


# Resolve src/vision for importing camera.py and sibling packages.
VISION_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
if VISION_DIR not in sys.path:
    sys.path.insert(0, VISION_DIR)

# Resolve src/intelligence for SessionManager import.
INTELLIGENCE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "intelligence")
)
if INTELLIGENCE_DIR not in sys.path:
    sys.path.insert(0, INTELLIGENCE_DIR)

from camera import Camera
from session_manager import SessionManager


class _FakeEyeTracker:
    """Minimal eye tracker stub used by camera._update_distraction_tracking()."""

    def __init__(self):
        self._cached_data = {
            "face_present": True,
            "face_facing_screen": True,
        }


def _build_mock_camera(session_manager: SessionManager) -> Camera:
    """Create a Camera instance without constructing YOLO/camera hardware objects."""
    camera = Camera.__new__(Camera)

    # Inject only the fields required by _update_distraction_tracking() and _flush_open_distractions().
    camera._session_manager = session_manager
    camera._DISTRACTION_COOLDOWN = 0.20  # Short cooldown keeps the test fast.
    camera._phone_distraction_start = None
    camera._phone_last_seen = None
    camera._look_away_distraction_start = None
    camera._look_away_last_seen = None
    camera._left_desk_distraction_start = None
    camera._left_desk_last_seen = None
    camera.eye_tracker = _FakeEyeTracker()

    return camera


def _tick(
    camera: Camera,
    *,
    phone_detected: bool,
    face_present: bool = True,
    face_facing_screen: bool = True,
    sleep_seconds: float = 0.05,
) -> None:
    """Advance one mock frame and let camera logic update distraction state."""
    camera.eye_tracker._cached_data["face_present"] = face_present
    camera.eye_tracker._cached_data["face_facing_screen"] = face_facing_screen
    camera._update_distraction_tracking(phone_detected)
    time.sleep(sleep_seconds)


def main() -> None:
    """Run a synthetic distraction sequence and persist it through SessionManager."""
    session_manager = SessionManager()
    session_manager.start_session()

    camera = _build_mock_camera(session_manager)

    # 1) Phone distraction block.
    for _ in range(5):
        _tick(camera, phone_detected=True, face_present=True, face_facing_screen=True)
    for _ in range(6):
        _tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

    # 2) Look-away distraction block (face present, not facing screen).
    for _ in range(5):
        _tick(camera, phone_detected=False, face_present=True, face_facing_screen=False)
    for _ in range(6):
        _tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

    # 3) Left-desk distraction block (no face present).
    for _ in range(5):
        _tick(camera, phone_detected=False, face_present=False, face_facing_screen=False)
    for _ in range(6):
        _tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

    # Flush any event that is still open, then end and score the session.
    camera._flush_open_distractions()
    session_manager.end_session()

    report = session_manager.session_report()

    print("Mock camera distraction test complete.")
    print(f"Session ID: {report['session_id']}")
    print(
        "Counts -> "
        f"phone: {report['phone_distractions']}, "
        f"look_away: {report['look_away_distractions']}, "
        f"left_desk: {report['left_desk_distractions']}"
    )
    print(
        "Times (s) -> "
        f"look_away_time: {report['look_away_time']}, "
        f"time_away: {report['time_away']}, "
        f"distraction_time: {report['distraction_time']}"
    )
    print(f"Score: {report['score']}, Focus %: {report['focus_percentage']}")


if __name__ == "__main__":
    main()
