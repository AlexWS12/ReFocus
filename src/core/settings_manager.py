import json
from pathlib import Path

from src.intelligence.session_manager import DistractionType

_SETTINGS_PATH = Path(__file__).resolve().parent.parent.parent / "settings.json"

_DEFAULTS = {
    "enabled_distractions": [dt.value for dt in DistractionType],
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
