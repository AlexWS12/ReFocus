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
    APP_DISTRACTION = "app_distraction"
    IDLE_DISTRACTION = "idle_distraction"   
   

class SessionManager:
    def __init__(self):
        self.db = get_database()
        self.current_session_id = None
        self.session_state = SessionState.READY
        self.session_start_time = None
        self.session_end_time = None
        self.distraction_events = []
        self.distraction_count = len(self.distraction_events)
    
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
    
    def end_session(self):
        if self.session_state not in [SessionState.IN_PROGRESS, SessionState.PAUSED]:
            raise Exception("No active session to end.")
        
        self.session_end_time = time.time()
        duration = int(self.session_end_time - self.session_start_time)
        
        # Update the session record with end time and duration
        cursor = self.db.cursor()
        cursor.execute('''
            UPDATE sessions SET end_time=?, duration=? WHERE id=?
        ''', (
            time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.session_end_time)),
            duration,
            self.current_session_id
        ))
        self.db.commit()
        
        # End session state
        # self.current_session_id = None
        self.session_state = SessionState.ENDED

        # session report 
    
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
