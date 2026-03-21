"""
Pytest configuration and fixtures for intelligence tests.
"""
import os
import pytest
from database import Database
from session_manager import SessionManager


TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_data.db")


@pytest.fixture
def test_db_path():
    """Return path to test database, cleaning up before and after test."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    yield TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def session_manager(test_db_path):
    """Fixture that provides a SessionManager backed by the test database.
    
    Yields:
        tuple: (SessionManager, Database) objects wired together.
               SessionManager will use the test DB for all operations.
    
    The test database is automatically cleaned up after the test.
    """
    db = Database(db_path=test_db_path)
    sm = SessionManager()
    # Point the session manager at the test DB connection
    sm.db = db._get_connection()
    yield sm, db
    
    # Close database connection before cleanup so file can be deleted
    if sm.db:
        sm.db.close()
    if db.conn:
        db.conn.close()
