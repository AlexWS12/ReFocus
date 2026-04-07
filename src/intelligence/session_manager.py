import json
import time
import math
from enum import Enum


class SessionState(Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    ENDED = "ended"

class DistractionType(Enum):
    # Canonical list of all distraction types tracked by the app.
    # Used as keys in distraction_data so there are no raw strings
    # floating around — adding a new type here forces you to handle it everywhere.
    # Default severity weights live in settings_manager._DEFAULT_WEIGHTS.
    PHONE_DISTRACTION = "phone_distraction"
    LOOK_AWAY_DISTRACTION = "look_away_distraction"
    LEFT_DESK_DISTRACTION = "left_desk_distraction"
    APP_DISTRACTION = "app_distraction"
    IDLE_DISTRACTION = "idle_distraction"


try:
    from src.intelligence.database import get_database
    from src.core import settings_manager
except ImportError:
    from database import get_database
    settings_manager = None

# Severity weights for each distraction type used in score calculation.
# Higher value = bigger penalty per event and per second distracted.
# Phone is the most penalized (intentional, high-impact) and idle the least (ambiguous).
# If a new DistractionType is added above, a corresponding entry must be added here.
SEVERITY = {
    DistractionType.PHONE_DISTRACTION:     1.00,
    DistractionType.APP_DISTRACTION:       0.75,
    DistractionType.LEFT_DESK_DISTRACTION: 0.60,
    DistractionType.LOOK_AWAY_DISTRACTION: 0.30,
    DistractionType.IDLE_DISTRACTION:      0.15,
}


# Maps each DistractionType enum value to its corresponding boolean column
# name in the user_settings table.  Used by UserConfig to translate between
# the Python enum world and the SQL schema.
# If a new DistractionType is added, a matching entry must be added here
# AND a new column must be added to the user_settings table in database.py.
_DTYPE_TO_SETTING_COL = {
    DistractionType.PHONE_DISTRACTION:     "phone_detection_enabled",
    DistractionType.LOOK_AWAY_DISTRACTION: "look_away_detection_enabled",
    DistractionType.LEFT_DESK_DISTRACTION: "left_desk_detection_enabled",
    DistractionType.APP_DISTRACTION:       "app_detection_enabled",
    DistractionType.IDLE_DISTRACTION:      "idle_detection_enabled",
}


class UserConfig:
    """Reads and writes per-distraction-type toggles from the user_settings table.

    This class is the single source of truth for which distraction types are
    currently enabled.  SessionManager reads from it at session start to freeze
    a snapshot; the settings UI writes to it when the user flips a toggle.

    The class is intentionally co-located with SessionManager rather than in a
    separate file because it is small (~40 lines), tightly coupled to
    DistractionType and get_database(), and only consumed by SessionManager.
    """

    def __init__(self):
        self.db = get_database()

    def get_enabled_types(self) -> set:
        """Returns the set of DistractionTypes currently enabled in user settings.

        Reads the singleton user_settings row and checks each boolean column.
        A column value of 1 (truthy) means the type is enabled.
        Used by SessionManager.start_session() to freeze the config snapshot.
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM user_settings WHERE id = 1")
        row = cursor.fetchone()
        return {
            dtype for dtype, col in _DTYPE_TO_SETTING_COL.items()
            if row[col]
        }

    def is_enabled(self, dtype: DistractionType) -> bool:
        """Check whether a single distraction type is currently enabled."""
        col = _DTYPE_TO_SETTING_COL[dtype]
        cursor = self.db.cursor()
        cursor.execute(f"SELECT {col} FROM user_settings WHERE id = 1")
        return bool(cursor.fetchone()[col])

    def set_enabled(self, dtype: DistractionType, enabled: bool) -> None:
        """Toggle a single distraction type on or off.

        Writes to the DB immediately and commits, so the change is persisted
        even if the app crashes before the next explicit commit.
        The column name is safe from injection because it comes from the
        hardcoded _DTYPE_TO_SETTING_COL mapping, never from user input.
        """
        col = _DTYPE_TO_SETTING_COL[dtype]
        now_str = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
        cursor = self.db.cursor()
        cursor.execute(
            f"UPDATE user_settings SET {col} = ?, updated_at = ? WHERE id = 1",
            (1 if enabled else 0, now_str)
        )
        self.db.commit()

    def get_all_settings(self) -> dict:
        """Returns {DistractionType: bool} for every distraction type.

        Useful for populating a settings UI with the current state of all toggles.
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM user_settings WHERE id = 1")
        row = cursor.fetchone()
        return {
            dtype: bool(row[col])
            for dtype, col in _DTYPE_TO_SETTING_COL.items()
        }


def _calculate_level(exp):
    # Maps cumulative XP to a level using ceil(exp / 110).
    # Calibrated so that exp=770 → level=7 (matches mock data; 770/110 = 7.0 exactly).
    # Level 1 is the floor — a player at 0 XP is still level 1, not level 0.
    # Every 110 XP earned crosses a level boundary:
    #   0–110 XP → level 1,  111–220 → level 2,  700–770 → level 7, etc.
    if exp <= 0:
        return 1
    return max(1, math.ceil(exp / 110))


class SessionManager:
    def __init__(self):
        self.db = get_database()
        # UserConfig provides read/write access to the user_settings table.
        # Used in start_session() to snapshot which distraction types are active.
        self.user_config = UserConfig()
        self.current_session_id = None
        self.session_state = SessionState.READY
        self.session_start_time = None
        self.session_end_time = None
        # Stores distraction events logged during the session.
        # Each entry is {"type": DistractionType, "time": seconds, "timestamp" : Time}.
        # Populated by log_distraction() and aggregated in end_session() before scoring.
        self.distraction_events = []
        # Pause tracking: total_pause_duration accumulates across all pause/resume
        # cycles; pause_start_time captures when the current pause began (None when
        # not paused). Both are subtracted from wall-clock time in end_session().
        self.total_pause_duration = 0
        self.pause_start_time = None
        # Frozen snapshot of enabled distraction types for the active session.
        # Set in start_session() by reading UserConfig, then used to:
        #   1. Gate log_distraction() — disabled types are silently discarded
        #   2. Gate calculate_score() — disabled types never contribute penalties
        #   3. Store as JSON in the sessions row — so PatternAnalyzer knows which
        #      types were active when analyzing historical data
        # None when no session is active (READY or after reset()).
        self._enabled_types = None
        # Snapshot of which distraction types are enabled for the current session.
        # Loaded from settings.json at session start so mid-session setting changes
        # don't alter a running session's tracking.
        self.enabled_distractions: set[DistractionType] = set(DistractionType)
        # Per-session severity weights used by calculate_score().
        # Loaded from settings.json via settings_manager; defaults are defined
        # in settings_manager._DEFAULT_WEIGHTS.
        self.severity_weights: dict[DistractionType, float] = (
            settings_manager.distraction_weights() if settings_manager is not None
            else {dt: 0 for dt in DistractionType}
        )

    def reset(self):
        # Resets all session state back to defaults, allowing the instance to be reused.
        # Must be called after a session ends before starting a new one.
        # Clears distraction_events so old data never bleeds into the next session.
        self.current_session_id = None
        self.session_state = SessionState.READY
        self.session_start_time = None
        self.session_end_time = None
        self.distraction_events = []
        # Pause tracking: total_pause_duration accumulates across all pause/resume
        # cycles; pause_start_time captures when the current pause began (None when
        # not paused). Both are subtracted from wall-clock time in end_session().
        self.total_pause_duration = 0
        self.pause_start_time = None
        # Clear the frozen config snapshot — it belonged to the ended session.
        # A fresh snapshot is taken in the next start_session() call.
        self._enabled_types = None
        self.enabled_distractions = set(DistractionType)
        self.severity_weights = (
            settings_manager.distraction_weights() if settings_manager is not None
            else {dt: 0 for dt in DistractionType}
        )

    def start_session(self):
        if self.session_state != SessionState.READY:
            raise Exception("Session is already in progress or paused.")

        # Freeze the user's current distraction settings for this session.
        # This snapshot is used to gate log_distraction() and stored in the
        # session row so pattern analysis knows which types were active.
        self._enabled_types = self.user_config.get_enabled_types()
        if settings_manager is not None:
            self.enabled_distractions = settings_manager.enabled_distractions()
            self.severity_weights = settings_manager.distraction_weights()

        self.session_start_time = time.time()
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT INTO sessions (start_time) VALUES (?)
        ''', (time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.session_start_time)),))
        self.db.commit()
        self.current_session_id = cursor.lastrowid
        self.session_state = SessionState.IN_PROGRESS

    def pause_session(self):
        # Transitions an active session into the PAUSED state and records the
        # wall-clock time the pause began. Only valid from IN_PROGRESS.
        # No DB write happens here — the session row is only finalized in end_session().
        if self.session_state != SessionState.IN_PROGRESS:
            raise Exception("Can only pause an active session.")
        self.pause_start_time = time.time()
        self.session_state = SessionState.PAUSED

    def resume_session(self):
        # Closes the current pause segment by accumulating its duration into
        # total_pause_duration, then returns to IN_PROGRESS.
        # Clearing pause_start_time signals that no pause is currently open,
        # preventing double-counting if end_session() checks the variable.
        if self.session_state != SessionState.PAUSED:
            raise Exception("Can only resume a paused session.")
        self.total_pause_duration += int(time.time() - self.pause_start_time)
        self.pause_start_time = None
        self.session_state = SessionState.IN_PROGRESS

    def log_distraction(self, dtype: DistractionType, duration_seconds: int):
        # Called by external detectors (camera, app monitor, etc.) whenever a distraction
        # is detected and resolved. Appends to distraction_events for later aggregation.
        # dtype:            which type of distraction occurred (DistractionType enum value)
        # duration_seconds: how long the distraction lasted in seconds
        if self.session_state != SessionState.IN_PROGRESS:
            raise Exception("Cannot log a distraction outside of an active session.")
        # Silently discard events for distraction types the user has disabled.
        # The Camera still runs its detectors (YOLO, gaze tracker, etc.) and calls
        # this method for every resolved event — filtering happens here so we don't
        # need to touch the complex detection pipeline.  The "is not None" guard
        # ensures that if _enabled_types was never set (shouldn't happen), we fall
        # back to allowing everything rather than blocking everything.
        if self._enabled_types is not None and dtype not in self._enabled_types:
            return
        self.distraction_events.append({
            "type": dtype,
            "time": duration_seconds, 
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
            })

    def end_session(self):
        if self.session_state not in [SessionState.IN_PROGRESS, SessionState.PAUSED]:
            raise Exception("No active session to end.")

        self.session_end_time = time.time()

        # If the session is being ended while paused, the active pause segment was
        # never closed by resume_session(). Close it here so the time is accounted for.
        if self.session_state == SessionState.PAUSED and self.pause_start_time is not None:
            self.total_pause_duration += int(self.session_end_time - self.pause_start_time)
            self.pause_start_time = None

        # Subtract all paused time from wall-clock elapsed to get the true session duration.
        # max(0, ...) guards against clock skew producing a negative value.
        duration = max(0, int(self.session_end_time - self.session_start_time) - self.total_pause_duration)

        # Aggregate raw distraction_events list into a dict keyed by DistractionType.
        # Rolls up individual events into total count and total time per type,
        # which is the format calculate_score expects.
        distraction_data = {}
        for event in self.distraction_events:
            dtype = event["type"]
            if dtype not in distraction_data:
                distraction_data[dtype] = {"count": 0, "time": 0}
            distraction_data[dtype]["count"] += 1
            distraction_data[dtype]["time"] += event["time"]

        score = self.calculate_score(duration, distraction_data)

        # Helper to safely pull a field from distraction_data without KeyError.
        # Returns 0 if the distraction type was never logged this session.
        def get(dtype, field):
            return distraction_data.get(dtype, {}).get(field, 0)

        # Per-type counts — map directly to their DB columns
        phone_count     = get(DistractionType.PHONE_DISTRACTION,     "count")
        look_away_count = get(DistractionType.LOOK_AWAY_DISTRACTION, "count")
        left_desk_count = get(DistractionType.LEFT_DESK_DISTRACTION, "count")
        app_count       = get(DistractionType.APP_DISTRACTION,       "count")
        idle_count      = get(DistractionType.IDLE_DISTRACTION,      "count")

        # Per-type times for the time-based columns
        # time_away      = left desk time (physically absent from desk)
        # look_away_time = look away time (eyes off screen but still at desk)
        time_away      = get(DistractionType.LEFT_DESK_DISTRACTION, "time")
        look_away_time = get(DistractionType.LOOK_AWAY_DISTRACTION, "time")

        # Derived session-level stats computed from the aggregated distraction_data
        distraction_time = sum(d["time"] for d in distraction_data.values())
        focused_time     = max(0, duration - distraction_time)
        total_events     = sum(d["count"] for d in distraction_data.values())
        focus_percentage = round((focused_time / duration) * 100, 1) if duration > 0 else 0

        # Calculate XP and coins earned for this session based on score and duration.
        points_earned, coins_earned = self._calculate_rewards(score, duration)

        # JSON snapshot of which distraction types were active for this session.
        # Stored as a sorted array of DistractionType string values, e.g.:
        #   '["app_distraction", "left_desk_distraction", "phone_distraction"]'
        # PatternAnalyzer reads this column to decide which ML features to include:
        # only types that were enabled for ALL sessions in the dataset are used as
        # features, so disabled-type zeros don't pollute the model.
        # NULL in legacy sessions (recorded before this feature) means "all types enabled".
        enabled_json = json.dumps(
            sorted(dt.value for dt in self._enabled_types)
        ) if self._enabled_types is not None else None

        # Write all populated columns back to the session row in one update,
        # including the newly computed points_earned and coins_earned.
        cursor = self.db.cursor()
        cursor.execute('''
            UPDATE sessions SET
                end_time=?, duration=?, score=?,
                focused_time=?, events=?, distraction_time=?,
                time_away=?, look_away_time=?,
                phone_distractions=?, look_away_distractions=?,
                left_desk_distractions=?, app_distractions=?, idle_distractions=?,
                focus_percentage=?,
                points_earned=?, coins_earned=?,
                enabled_distractions=?
            WHERE id=?
        ''', (
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.session_end_time)),
            duration, score,
            focused_time, total_events, distraction_time,
            time_away, look_away_time,
            phone_count, look_away_count, left_desk_count, app_count, idle_count,
            focus_percentage,
            points_earned, coins_earned,
            enabled_json,
            self.current_session_id
        ))

        # Update the singleton user_stats row with this session's contributions.
        # Called after the sessions commit so session data is safely stored first.
        self._update_user_stats(duration, points_earned, coins_earned, total_events, look_away_count)

        self._update_events_table()

        self.db.commit()

        self.session_state = SessionState.ENDED
        # Session data is intentionally kept in memory (current_session_id, distraction_events)
        # until reset() is explicitly called, so session_report() can still be accessed after end.

    def _calculate_rewards(self, score, duration):
        # Calculates XP (points_earned) and coins for a completed session.
        # Both scale with score * duration_minutes so longer, higher-quality
        # sessions earn disproportionately more — rewarding sustained focus.
        #
        # Constants calibrated against mock data (7 sessions → 770 XP, 177 coins):
        #   K_POINTS = 0.0175  ->  standard 75-min/score-80 session ≈ 105 XP
        #   K_COINS  = 0.004   ->  coins-to-XP ratio ≈ 23%, matching mock (177/770)
        #
        # Floor of 1 ensures even a zero-score or very short session earns something.
        K_POINTS = 0.0175
        K_COINS  = 0.004
        duration_minutes = duration / 60.0
        points_earned = max(1, round(score * duration_minutes * K_POINTS))
        coins_earned  = max(1, round(score * duration_minutes * K_COINS))
        return points_earned, coins_earned

    def _update_user_stats(self, duration, points_earned, coins_earned, total_events, look_away_count):
        # Updates the singleton user_stats row (id=1) after a session completes.
        # Reads the current row first so incremental values are computed in Python —
        # this avoids NULL-accumulation bugs and makes the logic explicit.
        # A single UPDATE ensures all stat changes are written atomically.
        cursor = self.db.cursor()

        # Read current snapshot of all fields we'll be incrementing
        cursor.execute('''
            SELECT total_sessions, total_time_spent, exp, coins,
                   total_distractions, total_look_aways
            FROM user_stats WHERE id = 1
        ''')
        row = cursor.fetchone()

        # Compute new values by adding session deltas to existing totals
        new_total_sessions     = row["total_sessions"]     + 1
        new_total_time_spent   = row["total_time_spent"]   + duration
        new_exp                = row["exp"]                + points_earned
        new_coins              = row["coins"]              + coins_earned
        new_total_distractions = row["total_distractions"] + total_events
        new_total_look_aways   = row["total_look_aways"]   + look_away_count

        # avg_focus_time recalculated from totals — more accurate than maintaining
        # a running average incrementally, which can drift across data imports
        new_avg_focus_time = new_total_time_spent / new_total_sessions

        # Level is always derived from cumulative exp — never stored independently
        new_level = _calculate_level(new_exp)

        now_str = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())

        # Write all changes in a single UPDATE to keep user_stats consistent.
        # current_pet and created_at are intentionally left untouched — they are
        # managed by other subsystems.
        cursor.execute('''
            UPDATE user_stats SET
                total_sessions=?, total_time_spent=?, exp=?, coins=?,
                total_distractions=?, total_look_aways=?,
                avg_focus_time=?, level=?, updated_at=?
            WHERE id = 1
        ''', (
            new_total_sessions, new_total_time_spent, new_exp, new_coins,
            new_total_distractions, new_total_look_aways,
            new_avg_focus_time, new_level, now_str
        ))
    
    def _update_events_table(self):
        cursor = self.db.cursor()
        for event in self.distraction_events:
            cursor.execute('''
                INSERT INTO events (session_id, event_type, timestamp, duration)
                VALUES (?, ?, ?, ?)
            ''', (
                self.current_session_id,
                event["type"].value,
                event["timestamp"],
                event["time"]
            ))

    def calculate_score(self, duration, distraction_data=None):
        # Computes a 0–100 focus score for the session.
        #
        # Formula: score = clamp(100 - penalty + duration_bonus, 0, 100)
        #
        # penalty:
        #   Sum of per-type penalties weighted by self.severity_weights
        #   (loaded from settings.json at session start).
        #   Each type contributes two components:
        #     - time_ratio * 50: proportional penalty based on what fraction of the
        #       session was spent distracted. The same 30s distraction hurts more in a
        #       10-min session than a 90-min session.
        #     - count * 2: flat penalty per event occurrence, so frequent brief
        #       distractions are still penalized even if total time is low.
        #   Both are multiplied by the type's severity weight.
        #
        # duration_bonus:
        #   Fixed flat bonus by session length tier. Rewards sustained effort and
        #   helps offset minor distractions in longer sessions.
        #   Tiers: <15m=0, 15–29m=+3, 30–59m=+5, 60–89m=+7, ≥90m=+10
        #
        # Untracked distraction types are assumed to be 0 (no distractions).
        if duration == 0:
            return 0

        penalty = 0
        if distraction_data:
            for dtype, data in distraction_data.items():
                # Skip disabled types so they never penalize the score.
                # This is technically redundant with the gate in log_distraction()
                # (disabled events are never appended), but serves as a safety net:
                # if calculate_score() is ever called directly with manually-constructed
                # distraction_data (e.g. in tests), disabled types still won't penalize.
                if self._enabled_types is not None and dtype not in self._enabled_types:
                    continue
                count = data.get("count", 0)
                time_spent = data.get("time", 0)
                if count == 0 and time_spent == 0:
                    continue
                time_ratio = time_spent / duration
                weight = self.severity_weights.get(dtype, 0)
                penalty += weight * (time_ratio * 50 + count * 2)

        duration_minutes = duration / 60
        if duration_minutes >= 90:
            duration_bonus = 10
        elif duration_minutes >= 60:
            duration_bonus = 7
        elif duration_minutes >= 30:
            duration_bonus = 5
        elif duration_minutes >= 15:
            duration_bonus = 3
        else:
            duration_bonus = 0

        score = 100 - penalty + duration_bonus
        return max(0, min(100, round(score)))

    def session_report(self):
        if self.session_state != SessionState.ENDED:
            raise Exception("Session is not yet ended. Please end the session to generate a report.")

        cursor = self.db.cursor()
        cursor.execute('''
            SELECT * FROM sessions WHERE id=?
        ''', (self.current_session_id,))
        session_data = cursor.fetchone()

        # Guard against the row not being found (e.g. DB was wiped mid-session)
        if session_data is None:
            raise Exception(f"Session record not found for id={self.current_session_id}.")

        # Access columns by name (sqlite3.Row supports this) so the report
        # doesn't silently break if the schema column order ever changes.
        report = {
            "session_id":             session_data["id"],
            "start_time":             session_data["start_time"],
            "end_time":               session_data["end_time"],
            "duration":               session_data["duration"],
            "focused_time":           session_data["focused_time"],
            "events":                 session_data["events"],
            "time_away":              session_data["time_away"],
            "look_away_time":         session_data["look_away_time"],
            "distraction_time":       session_data["distraction_time"],
            "phone_distractions":     session_data["phone_distractions"],
            "look_away_distractions": session_data["look_away_distractions"],
            "left_desk_distractions": session_data["left_desk_distractions"],
            "app_distractions":       session_data["app_distractions"],
            "idle_distractions":      session_data["idle_distractions"],
            "focus_percentage":       session_data["focus_percentage"],
            "score":                  session_data["score"],
            "points_earned":          session_data["points_earned"],
            "coins_earned":           session_data["coins_earned"],
        }

        return report
    
