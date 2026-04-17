# Focused unit tests for attention-tracker helper logic

import importlib
import os
import sys


def _import(primary: str, fallback: str, symbol: str):
    # Try project-root import first, then direct-run fallback
    for mod in (primary, fallback):
        try:
            return getattr(importlib.import_module(mod), symbol)
        except (ModuleNotFoundError, AttributeError):
            continue

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


gazeTracker = _import(
    "src.vision.Trackers.attention_tracker",
    "Trackers.attention_tracker",
    "gazeTracker",
)


def _make_tracker():
    tracker = gazeTracker.__new__(gazeTracker)
    tracker.yaw_threshold_deg = 18.0
    tracker.pitch_threshold_deg = 15.0
    tracker.roll_threshold_deg = 22.0
    tracker.attention_tolerance_deg = 3.0
    tracker.roll_tolerance_deg = 4.0
    tracker.missing_face_grace_seconds = 0.60
    tracker.calibrated_bounds = None
    tracker._last_face_seen_ts = 0.0
    tracker._last_face_present_data = None
    return tracker


def test_fallback_thresholds_include_small_runtime_tolerance():
    tracker = _make_tracker()

    assert tracker._is_face_facing_screen(20.0, 0.0, 0.0) is True
    assert tracker._is_face_facing_screen(22.5, 0.0, 0.0) is False


def test_calibrated_bounds_include_small_runtime_tolerance():
    tracker = _make_tracker()
    tracker.calibrated_bounds = {
        "yaw_min": -10.0,
        "yaw_max": 10.0,
        "pitch_min": -8.0,
        "pitch_max": 8.0,
        "roll_threshold_deg": 12.0,
    }

    assert tracker._is_face_facing_screen(12.0, 0.0, 0.0) is True
    assert tracker._is_face_facing_screen(14.1, 0.0, 0.0) is False


def test_recent_face_data_is_held_during_short_dropout():
    tracker = _make_tracker()
    tracker._last_face_seen_ts = 10.0
    tracker._last_face_present_data = {
        "face_present": True,
        "eyes_detected": True,
        "left_iris": None,
        "right_iris": None,
        "gaze_state_horizontal": "center",
        "gaze_state_vertical": "center",
        "yaw_deg": 0.0,
        "pitch_deg": 0.0,
        "roll_deg": 0.0,
        "raw_yaw_deg": 0.0,
        "raw_pitch_deg": 0.0,
        "raw_roll_deg": 0.0,
        "face_facing_screen": True,
        "attention_state": "attentive",
        "tracking_degraded": False,
    }

    result = tracker._stabilize_tracking_data(
        {
            "face_present": False,
            "eyes_detected": False,
            "left_iris": None,
            "right_iris": None,
            "gaze_state_horizontal": "unknown",
            "gaze_state_vertical": "unknown",
            "yaw_deg": 0.0,
            "pitch_deg": 0.0,
            "roll_deg": 0.0,
            "raw_yaw_deg": 0.0,
            "raw_pitch_deg": 0.0,
            "raw_roll_deg": 0.0,
            "face_facing_screen": False,
            "attention_state": "no_face",
            "tracking_degraded": False,
        },
        now=10.3,
    )

    assert result["face_present"] is True
    assert result["face_facing_screen"] is True
    assert result["tracking_degraded"] is True


def test_stale_dropout_eventually_returns_no_face():
    tracker = _make_tracker()
    tracker._last_face_seen_ts = 10.0
    tracker._last_face_present_data = {"face_present": True}

    result = tracker._stabilize_tracking_data(
        {
            "face_present": False,
            "eyes_detected": False,
            "left_iris": None,
            "right_iris": None,
            "gaze_state_horizontal": "unknown",
            "gaze_state_vertical": "unknown",
            "yaw_deg": 0.0,
            "pitch_deg": 0.0,
            "roll_deg": 0.0,
            "raw_yaw_deg": 0.0,
            "raw_pitch_deg": 0.0,
            "raw_roll_deg": 0.0,
            "face_facing_screen": False,
            "attention_state": "no_face",
            "tracking_degraded": False,
        },
        now=10.8,
    )

    assert result["face_present"] is False
    assert tracker._last_face_present_data is None
