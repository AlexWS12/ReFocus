from src.core.database_reader import DatabaseReader

class Achievement_Manager():
    def __init__(self):
        self.db = DatabaseReader()

    # Acesses the database to return users progress
    def get_progress(self):
        self.analytics = self.db.get_session_analytics()
        self.topbar = self.db.get_topbar_data()
        self.dates = self.db.get_session_dates()

        return {
            "First Step": self.analytics["total_sessions"],
            "On A Roll": 0,
            "Grind Mode": self.analytics["lifetime_focus_seconds"] // 3600,
            "Marathon": self.analytics["longest_focus_seconds"],
            "Consistent": 0,
            "Dedicated": 0,
            "Unstoppable": 0,
            "Level Up!": self.topbar["level"],
            "Scholar": self.topbar["level"],
            "XP Collector": self.topbar["exp"],
            "Pet Lover": 0,
            "Night Lover": 0,
        }

