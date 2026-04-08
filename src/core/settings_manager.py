import json
from pathlib import Path

from src.intelligence.session_manager import DistractionType

_SETTINGS_PATH = Path(__file__).resolve().parent.parent.parent / "settings.json"

# Canonical default severity weights for each distraction type.
# Higher value = bigger penalty per event and per second distracted.
# Phone is the most penalized (intentional, high-impact) and idle the least (ambiguous).
_DEFAULT_WEIGHTS: dict[str, float] = {
    DistractionType.PHONE_DISTRACTION.value:     1.00,
    DistractionType.APP_DISTRACTION.value:       0.75,
    DistractionType.LEFT_DESK_DISTRACTION.value: 0.60,
    DistractionType.LOOK_AWAY_DISTRACTION.value: 0.30,
    DistractionType.IDLE_DISTRACTION.value:      0.15,
}

# Detection thresholds used by the vision layer.
# Phone detection values start as None (must be set by calibration).
# Gaze angle defaults match attention_tracker.py hardcoded values.
_DEFAULT_DETECTION_THRESHOLDS = {
    "yolo_conf": None,
    "few_shot_similarity": None,
    "fallback_conf": None,
    "yaw_threshold_deg": 18.0,
    "pitch_threshold_deg": 15.0,
    "roll_threshold_deg": 22.0,
}

_DEFAULTS = {
    "enabled_distractions": [dt.value for dt in DistractionType],
    "distraction_weights": dict(_DEFAULT_WEIGHTS),
    "detection_thresholds": dict(_DEFAULT_DETECTION_THRESHOLDS),
}


def _deep_merge(defaults: dict, loaded: dict) -> dict:
    """Return *defaults* with any keys present in *loaded* overwritten."""
    merged = dict(defaults)
    for key, value in loaded.items():
        if key in merged:
            merged[key] = value
    return merged


def ensure_defaults() -> None:
    """Write the default settings.json to disk if it does not already exist."""
    if not _SETTINGS_PATH.exists():
        save(dict(_DEFAULTS))


def load() -> dict:
    """Read settings from disk, falling back to defaults for missing keys."""
    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH, "r") as f:
                data = json.load(f)
            return _deep_merge(_DEFAULTS, data)
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULTS)


def save(settings: dict) -> None:
    """Persist the full settings dict to disk."""
    with open(_SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def enabled_distractions() -> set[DistractionType]:
    """Convenience: load settings and return the enabled types as a set."""
    raw = load().get("enabled_distractions", [])
    result: set[DistractionType] = set()
    for value in raw:
        try:
            result.add(DistractionType(value))
        except ValueError:
            continue
    return result


def detection_thresholds() -> dict[str, float | None]:
    """Load settings and return detection thresholds.

    Returns a dict with keys matching _DEFAULT_DETECTION_THRESHOLDS.
    Phone detection values may be None if calibration hasn't run yet.
    """
    raw = load().get("detection_thresholds", {})
    result: dict[str, float | None] = {}
    for key, default in _DEFAULT_DETECTION_THRESHOLDS.items():
        val = raw.get(key)
        if val is None:
            result[key] = default
        else:
            try:
                result[key] = float(val)
            except (ValueError, TypeError):
                result[key] = default
    return result


def distraction_weights() -> dict[DistractionType, float]:
    """Load settings and return per-type severity weights.

    Falls back to _DEFAULT_WEIGHTS for any missing or invalid entries
    so calculate_score always has a complete map.
    """
    raw = load().get("distraction_weights", {})
    result: dict[DistractionType, float] = {}
    for dt in DistractionType:
        try:
            result[dt] = float(raw[dt.value])
        except (KeyError, ValueError, TypeError):
            result[dt] = _DEFAULT_WEIGHTS.get(dt.value, 0)
    return result
