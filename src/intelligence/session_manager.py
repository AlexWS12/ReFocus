import time
from enum import Enum
from database import get_database

class SessionState(Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    ENDED = "ended"

class DistractionType(Enum):
    PHONE_DISTRACTION = "phone_distraction"
    LOOK_AWAY_DISTRACTION = "look_away_distraction"
    LEFT_DESK_DISTRACTION = "left_desk_distraction"
    APP_DISTRACTION = "app_distraction"
    IDLE_DISTRACTION = "idle_distraction"

# Severity weights for each distraction type used in score calculation.
# Higher value = bigger penalty per event and per second distracted.
# The severities are relative and can be adjusted based on feedback and testing.
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
        # Each entry is {"type": DistractionType, "time": seconds}
        # Populated by log_distraction() during the session
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
        # Called externally by whatever detects the distraction (camera, app monitor, etc.)
        # dtype:            the type of distraction (must be a DistractionType enum value)
        # duration_seconds: how long the distraction lasted in seconds
        if self.session_state != SessionState.IN_PROGRESS:
            raise Exception("Cannot log a distraction outside of an active session.")
        self.distraction_events.append({"type": dtype, "time": duration_seconds})

    def end_session(self):
        if self.session_state not in [SessionState.IN_PROGRESS, SessionState.PAUSED]:
            raise Exception("No active session to end.")

        self.session_end_time = time.time()
        duration = int(self.session_end_time - self.session_start_time)

        # Add raw distraction events into {DistractionType: {count, time}}
        # so calculate_score can work with totals per type
        distraction_data = {}
        for event in self.distraction_events:
            dtype = event["type"]
            if dtype not in distraction_data:
                distraction_data[dtype] = {"count": 0, "time": 0}
            distraction_data[dtype]["count"] += 1
            distraction_data[dtype]["time"] += event["time"]

        score = self.calculate_score(duration, distraction_data)

        # Update the session record with end time, duration, and score
        cursor = self.db.cursor()
        cursor.execute('''
            UPDATE sessions SET end_time=?, duration=?, score=? WHERE id=?
        ''', (
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.session_end_time)),
            duration,
            score,
            self.current_session_id
        ))
        self.db.commit()

        # self.current_session_id = None
        self.session_state = SessionState.ENDED

    def calculate_score(self, duration, distraction_data=None):
        # Score formula:  score = clamp(100 - penalty + duration_bonus, 0, 100)
        #
        # penalty:        sum of per-type penalties, each weighted by severity.
        #                 penalty combines a time component (proportional to session duration)
        #                 and an event-count component so both frequency and length matter.
        #                 Using a ratio (time_spent / duration) means the same 30s distraction
        #                 hurts more in a 10-min session than a 90-min session.
        #
        # duration_bonus: flat reward for longer sessions. Helps offset minor distractions
        #                 in longer sessions and rewards sustained effort.
        #
        # Missing distraction types default to 0 (assumed no distractions of that type).
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
