import time
from enum import Enum
from database import get_database

class SessionState(Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    ENDED = "ended"

class DistractionType(Enum):
    # Canonical list of all distraction types tracked by the app.
    # Used as keys in SEVERITY and distraction_data so there are no raw strings
    # floating around — adding a new type here forces you to handle it everywhere.
    PHONE_DISTRACTION = "phone_distraction"
    LOOK_AWAY_DISTRACTION = "look_away_distraction"
    LEFT_DESK_DISTRACTION = "left_desk_distraction"
    APP_DISTRACTION = "app_distraction"
    IDLE_DISTRACTION = "idle_distraction"

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


class SessionManager:
    def __init__(self):
        self.db = get_database()
        self.current_session_id = None
        self.session_state = SessionState.READY
        self.session_start_time = None
        self.session_end_time = None
        # Stores distraction events logged during the session.
        # Each entry is {"type": DistractionType, "time": seconds}.
        # Populated by log_distraction() and aggregated in end_session() before scoring.
        self.distraction_events = []

    def start_session(self):
        if self.session_state != SessionState.READY:
            raise Exception("Session is already in progress or paused.")

        self.session_start_time = time.time()
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT INTO sessions (start_time) VALUES (?)
        ''', (time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.session_start_time)),))
        self.db.commit()
        self.current_session_id = cursor.lastrowid
        self.session_state = SessionState.IN_PROGRESS

    def log_distraction(self, dtype: DistractionType, duration_seconds: int):
        # Called by external detectors (camera, app monitor, etc.) whenever a distraction
        # is detected and resolved. Appends to distraction_events for later aggregation.
        # dtype:            which type of distraction occurred (DistractionType enum value)
        # duration_seconds: how long the distraction lasted in seconds
        if self.session_state != SessionState.IN_PROGRESS:
            raise Exception("Cannot log a distraction outside of an active session.")
        self.distraction_events.append({"type": dtype, "time": duration_seconds})

    def end_session(self):
        if self.session_state not in [SessionState.IN_PROGRESS, SessionState.PAUSED]:
            raise Exception("No active session to end.")

        self.session_end_time = time.time()
        duration = int(self.session_end_time - self.session_start_time)

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
        focused_time     = duration - distraction_time
        total_events     = sum(d["count"] for d in distraction_data.values())
        focus_percentage = round((focused_time / duration) * 100, 1) if duration > 0 else 0

        # Write all populated columns back to the session row in one update.
        # points_earned and coins_earned are left at their defaults (0) until
        # the rewards system is implemented.
        cursor = self.db.cursor()
        cursor.execute('''
            UPDATE sessions SET
                end_time=?, duration=?, score=?,
                focused_time=?, events=?, distraction_time=?,
                time_away=?, look_away_time=?,
                phone_distractions=?, look_away_distractions=?,
                left_desk_distractions=?, app_distractions=?, idle_distractions=?,
                focus_percentage=?
            WHERE id=?
        ''', (
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.session_end_time)),
            duration, score,
            focused_time, total_events, distraction_time,
            time_away, look_away_time,
            phone_count, look_away_count, left_desk_count, app_count, idle_count,
            focus_percentage,
            self.current_session_id
        ))
        self.db.commit()

        # self.current_session_id = None
        self.session_state = SessionState.ENDED

    def calculate_score(self, duration, distraction_data=None):
        # Computes a 0–100 focus score for the session.
        #
        # Formula: score = clamp(100 - penalty + duration_bonus, 0, 100)
        #
        # penalty:
        #   Sum of per-type penalties weighted by SEVERITY.
        #   Each type contributes two components:
        #     - time_ratio * 50: proportional penalty based on what fraction of the
        #       session was spent distracted. The same 30s distraction hurts more in a
        #       10-min session than a 90-min session.
        #     - count * 2: flat penalty per event occurrence, so frequent brief
        #       distractions are still penalized even if total time is low.
        #   Both are multiplied by the type's SEVERITY weight.
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
                count = data.get("count", 0)
                time_spent = data.get("time", 0)
                if count == 0 and time_spent == 0:
                    continue
                time_ratio = time_spent / duration
                penalty += SEVERITY[dtype] * (time_ratio * 50 + count * 2)

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
        return max(0, min(100, round(score, 1)))

    def session_report(self):
        if self.session_state != SessionState.ENDED:
            raise Exception("Session is not yet ended. Please end the session to generate a report.")

        cursor = self.db.cursor()
        cursor.execute('''
            SELECT * FROM sessions WHERE id=?
        ''', (self.current_session_id,))
        session_data = cursor.fetchone()

        report = {
            "session_id": session_data[0],
            "start_time": session_data[1],
            "end_time": session_data[2],
            "duration": session_data[3],
            "focused_time": session_data[4],
            "events": session_data[5],
            "time_away": session_data[6],
            "look_away_time": session_data[7],
            "distraction_time": session_data[8],
            "phone_distractions": session_data[9],
            "look_away_distractions": session_data[10],
            "left_desk_distractions": session_data[11],
            "app_distractions": session_data[12],
            "idle_distractions": session_data[13],
            "focus_percentage": session_data[14],
            "score": session_data[15],
            "points_earned": session_data[16],
            "coins_earned": session_data[17]
        }

        return report
