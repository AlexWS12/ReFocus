"""
Pytest-based functional tests for SessionManager.

Tests session lifecycle, pause/resume, rewards calculation,
user_stats updates, and guard checks.

Run with:
    pytest src/intelligence/tests/test_session_manager.py -v

Or directly:
    python src/intelligence/tests/test_session_manager.py
"""

import pytest
import time
try:
    from session_manager import SessionManager, SessionState, DistractionType, _calculate_level
except ModuleNotFoundError:
    import os
    import sys

    # Allow direct execution (python src/intelligence/tests/test_session_manager.py)
    # by resolving the sibling intelligence package at runtime.
    _INTELLIGENCE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    if _INTELLIGENCE_DIR not in sys.path:
        sys.path.insert(0, _INTELLIGENCE_DIR)
    from session_manager import SessionManager, SessionState, DistractionType, _calculate_level



class TestSessionManagerLifecycle:
    """Tests for basic session lifecycle operations."""

    def test_session_lifecycle(self, session_manager):
        """Start → log distractions → end → report produces valid data."""
        sm, db = session_manager

        sm.start_session()
        assert sm.session_state == SessionState.IN_PROGRESS

        sm.log_distraction(DistractionType.PHONE_DISTRACTION, 30)
        sm.log_distraction(DistractionType.LOOK_AWAY_DISTRACTION, 10)
        assert len(sm.distraction_events) == 2

        sm.end_session()
        assert sm.session_state == SessionState.ENDED

        report = sm.session_report()
        assert report["session_id"] is not None
        assert report["score"] >= 0
        assert report["points_earned"] >= 1
        assert report["coins_earned"] >= 1
        assert report["phone_distractions"] == 1
        assert report["phone_time"] == 30
        assert report["look_away_distractions"] == 1

    def test_pause_resume(self, session_manager):
        """Pause and resume transitions work correctly."""
        sm, db = session_manager

        sm.start_session()
        sm.pause_session()
        assert sm.session_state == SessionState.PAUSED
        assert sm.pause_start_time is not None

        time.sleep(1)
        sm.resume_session()
        assert sm.session_state == SessionState.IN_PROGRESS
        assert sm.pause_start_time is None
        assert sm.total_pause_duration >= 1

        sm.end_session()

    def test_end_while_paused(self, session_manager):
        """Ending a session while paused closes the open pause segment."""
        sm, db = session_manager

        sm.start_session()
        sm.pause_session()
        time.sleep(1)
        sm.end_session()

        report = sm.session_report()
        # Duration should be ~0 because the entire session was paused
        assert report["duration"] <= 1

    def test_multiple_pause_cycles(self, session_manager):
        """Multiple pause/resume cycles accumulate correctly."""
        sm, db = session_manager

        sm.start_session()
        for _ in range(3):
            sm.pause_session()
            time.sleep(1)
            sm.resume_session()

        assert sm.total_pause_duration >= 3
        sm.end_session()

    def test_reset(self, session_manager):
        """Reset clears all state including pause tracking."""
        sm, db = session_manager

        sm.start_session()
        sm.pause_session()
        time.sleep(1)
        sm.resume_session()
        sm.log_distraction(DistractionType.IDLE_DISTRACTION, 5)
        sm.end_session()

        sm.reset()
        assert sm.session_state == SessionState.READY
        assert sm.total_pause_duration == 0
        assert sm.pause_start_time is None
        assert sm.distraction_events == []
        assert sm.current_session_id is None

        # Can start a new session after reset
        sm.start_session()
        assert sm.session_state == SessionState.IN_PROGRESS
        sm.end_session()


class TestRewardsAndStats:
    """Tests for rewards calculation and user stats updates."""

    def test_rewards_calculation(self, session_manager):
        """Rewards scale with score and duration."""
        sm, db = session_manager

        # Test the formula directly: score=80, duration=4500s (75 min)
        points, coins = sm._calculate_rewards(80, 4500)
        # Expected: 80 * 75 * 0.0175 = 105, 80 * 75 * 0.004 = 24
        assert points == 105
        assert coins == 24

        # Floor of 1 for tiny sessions
        points_min, coins_min = sm._calculate_rewards(0, 0)
        assert points_min == 1
        assert coins_min == 1

    def test_user_stats_update(self, session_manager):
        """user_stats row is updated after each session ends."""
        sm, db = session_manager

        # Check initial state
        cursor = sm.db.cursor()
        cursor.execute("SELECT total_sessions, exp, coins, level FROM user_stats WHERE id = 1")
        before = cursor.fetchone()
        assert before["total_sessions"] == 0
        assert before["exp"] == 0

        sm.start_session()
        sm.end_session()

        cursor.execute("SELECT total_sessions, exp, coins, level FROM user_stats WHERE id = 1")
        after = cursor.fetchone()
        assert after["total_sessions"] == 1
        assert after["exp"] >= 1
        assert after["coins"] >= 1
        assert after["level"] >= 1

    def test_calculate_level(self):
        """Level formula: ceil(exp / 110), floor of 1."""
        assert _calculate_level(0) == 1
        assert _calculate_level(-10) == 1
        assert _calculate_level(110) == 1
        assert _calculate_level(111) == 2
        assert _calculate_level(770) == 7
        assert _calculate_level(1100) == 10


class TestScoreCalculation:
    """Tests for score calculation logic."""

    def test_score_calculation(self, session_manager):
        """Score formula: 100 - penalty + duration_bonus, clamped to 0-100."""
        sm, db = session_manager

        # Perfect session (no distractions, 60 min) → 100 + 7 bonus, clamped to 100
        score = sm.calculate_score(3600, {})
        assert score == 100

        # Zero duration → 0
        score = sm.calculate_score(0, {})
        assert score == 0

        # Heavy distractions should reduce score significantly
        heavy = {
            DistractionType.PHONE_DISTRACTION: {"count": 10, "time": 1800}
        }
        score = sm.calculate_score(3600, heavy)
        assert score < 70


class TestGuardChecks:
    """Tests for invalid state transitions and guard checks."""

    def test_invalid_state_transitions(self, session_manager):
        """Invalid state transitions raise exceptions."""
        sm, db = session_manager

        # Can't pause/resume from READY
        with pytest.raises(Exception):
            sm.pause_session()

        with pytest.raises(Exception):
            sm.resume_session()

        sm.start_session()

        # Can't resume from IN_PROGRESS
        with pytest.raises(Exception):
            sm.resume_session()

        sm.pause_session()

        # Can't log distractions while PAUSED
        with pytest.raises(Exception):
            sm.log_distraction(DistractionType.PHONE_DISTRACTION, 5)

        # Can't pause while already PAUSED
        with pytest.raises(Exception):
            sm.pause_session()

        sm.end_session()

        # Can't end an already-ended session
        with pytest.raises(Exception):
            sm.end_session()


if __name__ == "__main__":
    # Keep a direct-run entrypoint for local debugging while using pytest as the source of truth.
    pytest.main([__file__, "-v"])
