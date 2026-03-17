"""
Functional tests for SessionManager: session lifecycle, pause/resume,
rewards calculation, user_stats updates, and guard checks.

Run from src/intelligence/:
    python tests/test_session_manager.py
"""

import sys
import os
import time

# Add parent directory to path so we can import database and session_manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import Database
from session_manager import SessionManager, SessionState, DistractionType, _calculate_level

# Use a temporary DB file so tests don't pollute the real data.db
TEST_DB = os.path.join(os.path.dirname(__file__), "test_data.db")

passed = 0
failed = 0


def assert_eq(actual, expected, msg=""):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {msg} — expected {expected!r}, got {actual!r}")


def assert_true(condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {msg}")


def assert_raises(fn, msg=""):
    """Verify that calling fn() raises an Exception."""
    global passed, failed
    try:
        fn()
        failed += 1
        print(f"  FAIL: {msg} — expected exception, none raised")
    except Exception:
        passed += 1


def fresh_session_manager():
    """Returns a SessionManager backed by the test DB."""
    db = Database(db_path=TEST_DB)
    sm = SessionManager()
    # Point the session manager at the test DB connection
    sm.db = db._get_connection()
    return sm, db


def cleanup():
    """Remove the test database file."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_session_lifecycle():
    """Start → log distractions → end → report produces valid data."""
    print("Test: session lifecycle")
    sm, db = fresh_session_manager()

    sm.start_session()
    assert_eq(sm.session_state, SessionState.IN_PROGRESS, "state after start")

    sm.log_distraction(DistractionType.PHONE_DISTRACTION, 30)
    sm.log_distraction(DistractionType.LOOK_AWAY_DISTRACTION, 10)
    assert_eq(len(sm.distraction_events), 2, "distraction count in memory")

    sm.end_session()
    assert_eq(sm.session_state, SessionState.ENDED, "state after end")

    report = sm.session_report()
    assert_true(report["session_id"] is not None, "report has session_id")
    assert_true(report["score"] >= 0, "score is non-negative")
    assert_true(report["points_earned"] >= 1, "XP floor of 1")
    assert_true(report["coins_earned"] >= 1, "coins floor of 1")
    assert_eq(report["phone_distractions"], 1, "phone distraction count")
    assert_eq(report["look_away_distractions"], 1, "look-away distraction count")

    db.close()
    cleanup()


def test_pause_resume():
    """Pause and resume transitions work correctly."""
    print("Test: pause/resume")
    sm, db = fresh_session_manager()

    sm.start_session()
    sm.pause_session()
    assert_eq(sm.session_state, SessionState.PAUSED, "state after pause")
    assert_true(sm.pause_start_time is not None, "pause_start_time set")

    time.sleep(1)
    sm.resume_session()
    assert_eq(sm.session_state, SessionState.IN_PROGRESS, "state after resume")
    assert_true(sm.pause_start_time is None, "pause_start_time cleared")
    assert_true(sm.total_pause_duration >= 1, "pause duration accumulated")

    sm.end_session()
    db.close()
    cleanup()


def test_end_while_paused():
    """Ending a session while paused closes the open pause segment."""
    print("Test: end while paused")
    sm, db = fresh_session_manager()

    sm.start_session()
    sm.pause_session()
    time.sleep(1)
    sm.end_session()

    report = sm.session_report()
    # Duration should be ~0 because the entire session was paused
    assert_true(report["duration"] <= 1, "duration near 0 when fully paused")

    db.close()
    cleanup()


def test_multiple_pause_cycles():
    """Multiple pause/resume cycles accumulate correctly."""
    print("Test: multiple pause cycles")
    sm, db = fresh_session_manager()

    sm.start_session()
    for _ in range(3):
        sm.pause_session()
        time.sleep(1)
        sm.resume_session()

    assert_true(sm.total_pause_duration >= 3, "3 pause cycles accumulated")
    sm.end_session()

    db.close()
    cleanup()


def test_rewards_calculation():
    """Rewards scale with score and duration."""
    print("Test: rewards calculation")
    sm, db = fresh_session_manager()

    # Test the formula directly: score=80, duration=4500s (75 min)
    points, coins = sm._calculate_rewards(80, 4500)
    # Expected: 80 * 75 * 0.0175 = 105, 80 * 75 * 0.004 = 24
    assert_eq(points, 105, "XP for standard session")
    assert_eq(coins, 24, "coins for standard session")

    # Floor of 1 for tiny sessions
    points_min, coins_min = sm._calculate_rewards(0, 0)
    assert_eq(points_min, 1, "XP floor of 1")
    assert_eq(coins_min, 1, "coins floor of 1")

    db.close()
    cleanup()


def test_user_stats_update():
    """user_stats row is updated after each session ends."""
    print("Test: user_stats update")
    sm, db = fresh_session_manager()

    # Check initial state
    cursor = sm.db.cursor()
    cursor.execute("SELECT total_sessions, exp, coins, level FROM user_stats WHERE id = 1")
    before = cursor.fetchone()
    assert_eq(before["total_sessions"], 0, "initial total_sessions")
    assert_eq(before["exp"], 0, "initial exp")

    sm.start_session()
    sm.end_session()

    cursor.execute("SELECT total_sessions, exp, coins, level FROM user_stats WHERE id = 1")
    after = cursor.fetchone()
    assert_eq(after["total_sessions"], 1, "total_sessions incremented")
    assert_true(after["exp"] >= 1, "exp increased")
    assert_true(after["coins"] >= 1, "coins increased")
    assert_true(after["level"] >= 1, "level at least 1")

    db.close()
    cleanup()


def test_calculate_level():
    """Level formula: ceil(exp / 110), floor of 1."""
    print("Test: calculate level")
    assert_eq(_calculate_level(0), 1, "level at 0 XP")
    assert_eq(_calculate_level(-10), 1, "level at negative XP")
    assert_eq(_calculate_level(110), 1, "level at 110 XP")
    assert_eq(_calculate_level(111), 2, "level at 111 XP")
    assert_eq(_calculate_level(770), 7, "level at 770 XP (mock data)")
    assert_eq(_calculate_level(1100), 10, "level at 1100 XP")


def test_guard_checks():
    """Invalid state transitions raise exceptions."""
    print("Test: guard checks")
    sm, db = fresh_session_manager()

    # Can't pause/resume from READY
    assert_raises(lambda: sm.pause_session(), "pause from READY")
    assert_raises(lambda: sm.resume_session(), "resume from READY")

    sm.start_session()

    # Can't resume from IN_PROGRESS
    assert_raises(lambda: sm.resume_session(), "resume from IN_PROGRESS")

    sm.pause_session()

    # Can't log distractions while PAUSED
    assert_raises(
        lambda: sm.log_distraction(DistractionType.PHONE_DISTRACTION, 5),
        "log distraction while PAUSED"
    )

    # Can't pause while already PAUSED
    assert_raises(lambda: sm.pause_session(), "pause from PAUSED")

    sm.end_session()

    # Can't end an already-ended session
    assert_raises(lambda: sm.end_session(), "end from ENDED")

    db.close()
    cleanup()


def test_reset():
    """Reset clears all state including pause tracking."""
    print("Test: reset")
    sm, db = fresh_session_manager()

    sm.start_session()
    sm.pause_session()
    time.sleep(1)
    sm.resume_session()
    sm.log_distraction(DistractionType.IDLE_DISTRACTION, 5)
    sm.end_session()

    sm.reset()
    assert_eq(sm.session_state, SessionState.READY, "state after reset")
    assert_eq(sm.total_pause_duration, 0, "pause duration cleared")
    assert_eq(sm.pause_start_time, None, "pause_start_time cleared")
    assert_eq(sm.distraction_events, [], "distraction_events cleared")
    assert_eq(sm.current_session_id, None, "session_id cleared")

    # Can start a new session after reset
    sm.start_session()
    assert_eq(sm.session_state, SessionState.IN_PROGRESS, "new session after reset")
    sm.end_session()

    db.close()
    cleanup()


def test_score_calculation():
    """Score formula: 100 - penalty + duration_bonus, clamped to 0-100."""
    print("Test: score calculation")
    sm, db = fresh_session_manager()

    # Perfect session (no distractions, 60 min) → 100 + 7 bonus, clamped to 100
    score = sm.calculate_score(3600, {})
    assert_eq(score, 100, "perfect 60-min session")

    # Zero duration → 0
    score = sm.calculate_score(0, {})
    assert_eq(score, 0, "zero duration")

    # Heavy distractions should reduce score significantly
    # 10 phone events (penalty: 10*2*1.0=20) + 50% time ratio (0.5*50*1.0=25)
    # Total penalty=45, bonus=7, score=62 — well below the perfect 100
    heavy = {
        DistractionType.PHONE_DISTRACTION: {"count": 10, "time": 1800}
    }
    score = sm.calculate_score(3600, heavy)
    assert_true(score < 70, "heavy phone distractions reduce score below 70")

    db.close()
    cleanup()


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Clean up any leftover test DB before starting
    cleanup()

    test_session_lifecycle()
    test_pause_resume()
    test_end_while_paused()
    test_multiple_pause_cycles()
    test_rewards_calculation()
    test_user_stats_update()
    test_calculate_level()
    test_guard_checks()
    test_reset()
    test_score_calculation()

    # Final cleanup
    cleanup()

    print()
    print(f"Results: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")
