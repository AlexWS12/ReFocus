# Pytest configuration and fixtures for vision tests
import importlib
import os
import sys
import pytest


def _import(primary: str, fallback: str, symbol: str):
    # Try project-root import first, then pytest-pythonpath fallback
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
SessionManager = _import("src.intelligence.session_manager", "session_manager", "SessionManager")


class _FakeEyeTracker:
    # Minimal eye tracker stub used by camera._update_distraction_tracking()

    def __init__(self):
        self._cached_data = {
            "face_present": True,
            "face_facing_screen": True,
        }


@pytest.fixture
def mock_camera(vision_session_manager):
    # Fixture that provides a mock Camera without hardware initialization
    session_manager = vision_session_manager

    # Create Camera instance without calling __init__ (no hardware)
    camera = Camera.__new__(Camera)

    # Inject only the fields required by _update_distraction_tracking() and _flush_open_distractions().
    camera._session_manager = session_manager
    camera._DISTRACTION_COOLDOWN = 0.20  # Short cooldown for fast tests
    camera._LEFT_DESK_TRANSITION_SECONDS = 0.20  # Short transition so left-desk tests complete quickly
    camera._phone_distraction_start = None
    camera._phone_last_seen = None
    camera._look_away_distraction_start = None
    camera._look_away_last_seen = None
    camera._left_desk_distraction_start = None
    camera._left_desk_last_seen = None
    camera.eye_tracker = _FakeEyeTracker()

    yield camera


@pytest.fixture
def vision_session_manager():
    # Fixture that provides a SessionManager for vision tests
    Database = _import("src.intelligence.database", "database", "Database")

    # Use a temporary test DB so vision tests don't pollute data.db
    test_db_path = os.path.join(os.path.dirname(__file__), "vision_test_data.db")
    
    # Clean up any leftover test DB before starting
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    db = Database(db_path=test_db_path)
    session_manager = SessionManager()
    session_manager.db = db._get_connection()
    
    yield session_manager
    
    # Close database connection before cleanup so file can be deleted
    if session_manager.db:
        session_manager.db.close()
    if db.conn:
        db.conn.close()
    
    # Clean up test DB after test completes
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

