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
    "active_profile": None,
    "profiles": {},
    "enabled_distractions": [dt.value for dt in DistractionType],
    "distraction_weights": dict(_DEFAULT_WEIGHTS),
    "detection_thresholds": dict(_DEFAULT_DETECTION_THRESHOLDS),
    "used_dark_mode": False,
    "unlocked_achievements": [],
}


def _deep_merge(defaults: dict, loaded: dict) -> dict:
    # Return *defaults* with any keys present in *loaded* overwritten
    merged = dict(defaults)
    for key, value in loaded.items():
        if key not in merged:
            continue
        if isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def ensure_defaults() -> None:
    # Write the default settings.json to disk if it does not already exist
    if not _SETTINGS_PATH.exists():
        save(dict(_DEFAULTS))


def load() -> dict:
    # Read settings from disk, falling back to defaults for missing keys
    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH, "r") as f:
                data = json.load(f)
            return _deep_merge(_DEFAULTS, data)
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULTS)


def save(settings: dict) -> None:
    # Persist the full settings dict to disk
    with open(_SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def enabled_distractions() -> set[DistractionType]:
    # Convenience: load settings and return the enabled types as a set
    raw = load().get("enabled_distractions", [])
    result: set[DistractionType] = set()
    for value in raw:
        try:
            result.add(DistractionType(value))
        except ValueError:
            continue
    return result


def detection_thresholds() -> dict[str, float | None]:
    # Load settings and return detection thresholds
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


def list_profiles() -> list[str]:
    # Return sorted profile names
    return sorted(load().get("profiles", {}).keys())


def load_profile(name: str) -> dict | None:
    # Return the settings snapshot for a named profile, or None if not found
    return load().get("profiles", {}).get(name)


def save_profile(name: str, profile: dict) -> None:
    # Save or overwrite a named profile
    settings = load()
    settings.setdefault("profiles", {})[name] = profile
    settings["active_profile"] = name
    save(settings)


def delete_profile(name: str) -> None:
    # Remove a named profile
    settings = load()
    settings.get("profiles", {}).pop(name, None)
    if settings.get("active_profile") == name:
        settings["active_profile"] = None
    save(settings)


def active_profile_name() -> str | None:
    return load().get("active_profile")


def distraction_weights() -> dict[DistractionType, float]:
    # Load settings and return per-type severity weights
    raw = load().get("distraction_weights", {})
    result: dict[DistractionType, float] = {}
    for dt in DistractionType:
        try:
            result[dt] = float(raw[dt.value])
        except (KeyError, ValueError, TypeError):
            result[dt] = _DEFAULT_WEIGHTS.get(dt.value, 0)
    return result
