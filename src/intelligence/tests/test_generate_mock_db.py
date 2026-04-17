# Tests for the seeded mock database generator used by the UI

import sqlite3

import pytest

try:
    from generate_mock_db import create_mock_database
except ModuleNotFoundError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from generate_mock_db import create_mock_database


def test_create_mock_database_seeds_expected_data(tmp_path):
    # Mock DB builder should create schema and populate representative UI data
    db_path = tmp_path / "mock_data.db"

    created_path = create_mock_database(str(db_path))

    assert created_path == str(db_path)
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        achievement_count = conn.execute("SELECT COUNT(*) FROM achievements").fetchone()[0]
        user_stats = conn.execute(
            "SELECT level, total_sessions, coins, exp, current_pet FROM user_stats WHERE id = 1"
        ).fetchone()
        latest_session = conn.execute(
            "SELECT score, focus_percentage FROM sessions WHERE id = 4"
        ).fetchone()
    finally:
        conn.close()

    assert session_count == 20
    assert event_count == 68
    assert achievement_count == 10
    assert user_stats == (19, 20, 497, 2085, "fox")
    assert latest_session == (98, 95.0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))