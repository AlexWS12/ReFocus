# Pytest-based tests for camera distraction tracking

import importlib
import os
import sys
import time
from typing import Any
import pytest


def _import(primary: str, fallback: str, symbol: str):
    # Try project-root import first, then pytest-pythonpath / direct-run fallback
    for mod in (primary, fallback):
        try:
            return getattr(importlib.import_module(mod), symbol)
        except (ModuleNotFoundError, AttributeError):
            continue

    # Direct-run fallback: add project root once when this file is executed as a script.
    project_root = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
    )
    direct_paths = [
        project_root,
        os.path.join(project_root, "src", "vision"),
        os.path.join(project_root, "src", "intelligence"),
    ]
    for path in direct_paths:
        if path not in sys.path:
            sys.path.insert(0, path)

    for mod in (primary, fallback):
        try:
            return getattr(importlib.import_module(mod), symbol)
        except (ModuleNotFoundError, AttributeError):
            continue

    raise ImportError(f"Cannot resolve {symbol} from {primary} or {fallback}")


Camera = _import("src.vision.camera", "camera", "Camera")


def tick(
    camera: Any,
    *,
    phone_detected: bool,
    face_present: bool = True,
    face_facing_screen: bool = True,
    sleep_seconds: float = 0.05,
) -> None:
    # Advance one mock frame and let camera logic update distraction state
    camera.eye_tracker._cached_data["face_present"] = face_present
    camera.eye_tracker._cached_data["face_facing_screen"] = face_facing_screen
    camera._update_distraction_tracking(phone_detected)
    time.sleep(sleep_seconds)


class TestCameraDistractions:
    # Tests for camera-based distraction tracking

    def test_phone_distraction(self, mock_camera, vision_session_manager):
        # Verify phone distraction is detected and logged
        session_manager = vision_session_manager
        session_manager.start_session()

        camera = mock_camera

        # Simulate phone detected for 5 ticks
        for _ in range(5):
            tick(camera, phone_detected=True, face_present=True, face_facing_screen=True)

        # Cooldown period (phone not detected)
        for _ in range(6):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

        # Flush and end session
        camera._flush_open_distractions()
        session_manager.end_session()

        report = session_manager.session_report()
        
        # Verify phone distraction was logged
        assert report["phone_distractions"] == 1, "Should detect 1 phone distraction"
        assert report["session_id"] is not None, "Should have a session ID"
        assert report["score"] >= 0, "Score should be non-negative"

    def test_look_away_distraction(self, mock_camera, vision_session_manager):
        # Verify look-away distraction is detected and logged
        session_manager = vision_session_manager
        session_manager.start_session()

        camera = mock_camera

        # Simulate look-away (face present but not facing screen) for 5 ticks
        for _ in range(5):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=False)

        # Face back to screen (recovery)
        for _ in range(6):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

        # Flush and end session
        camera._flush_open_distractions()
        session_manager.end_session()

        report = session_manager.session_report()
        
        # Verify look-away distraction was logged
        assert report["look_away_distractions"] == 1, "Should detect 1 look-away distraction"
        assert report["look_away_time"] > 0, "Look-away time should be positive"

    def test_left_desk_distraction(self, mock_camera, vision_session_manager):
        # Verify left-desk distraction is detected and logged
        session_manager = vision_session_manager
        session_manager.start_session()

        camera = mock_camera

        # Simulate left desk (no face present) for 5 ticks
        for _ in range(5):
            tick(camera, phone_detected=False, face_present=False, face_facing_screen=False)

        # Face back (recovery)
        for _ in range(6):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

        # Flush and end session
        camera._flush_open_distractions()
        session_manager.end_session()

        report = session_manager.session_report()
        
        # Verify left-desk distraction was logged
        assert report["left_desk_distractions"] == 1, "Should detect 1 left-desk distraction"
        assert report["time_away"] > 0, "Time away should be positive"

    def test_all_three_distractions(self, mock_camera, vision_session_manager):
        # Verify that all three distraction types can be logged in one session
        session_manager = vision_session_manager
        session_manager.start_session()

        camera = mock_camera

        # 1) Phone distraction block
        for _ in range(5):
            tick(camera, phone_detected=True, face_present=True, face_facing_screen=True)
        for _ in range(6):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

        # 2) Look-away distraction block
        for _ in range(5):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=False)
        for _ in range(6):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

        # 3) Left-desk distraction block
        for _ in range(5):
            tick(camera, phone_detected=False, face_present=False, face_facing_screen=False)
        for _ in range(6):
            tick(camera, phone_detected=False, face_present=True, face_facing_screen=True)

        # Flush and end session
        camera._flush_open_distractions()
        session_manager.end_session()

        report = session_manager.session_report()
        
        # Verify all three distraction types were logged
        assert report["phone_distractions"] >= 1, "Should log phone distraction"
        assert report["look_away_distractions"] >= 1, "Should log look-away distraction"
        assert report["left_desk_distractions"] >= 1, "Should log left-desk distraction"
        assert report["distraction_time"] > 0, "Total distraction time should be positive"
        assert 0 <= report["score"] <= 100, "Score should be between 0 and 100"


if __name__ == "__main__":
    # Keep a direct-run entrypoint for local debugging while using pytest as the source of truth.
    pytest.main([__file__, "-v"])
