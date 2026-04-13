from src.core.database_reader import DatabaseReader
from PySide6.QtWidgets import QApplication
from collections import Counter
from datetime import date, timedelta, datetime
from src.core import settings_manager

from src.intelligence.pet_manager import PetManager

class Achievement_Manager():
    def __init__(self):
        self.db = DatabaseReader()
        self.pm = PetManager()
        self.app = QApplication.instance()

    # Acesses the database to return users progress
    def get_progress(self):
        analytics = self.db.get_session_analytics()
        topbar = self.db.get_topbar_data()
        dates = self.db.get_session_dates()

        day_counts = [row["start_time"][:10] for row in dates]
        counts = Counter(day_counts)
        unique_days = sorted(set(day_counts), reverse=True)

        streak = 0
        for i, day in enumerate(unique_days):
            raw_date = datetime.strptime(day, "%Y-%m-%d").date()
            if raw_date == date.today() - timedelta(days=i):
                streak += 1
            else:
                break

        return {
            "First Step": analytics["total_sessions"],
            "On A Roll": max(counts.values()) if day_counts else 0,
            "Grind Mode": analytics["lifetime_focus_seconds"] // 3600,
            "Marathon": analytics["longest_focus_seconds"],
            "Consistent": streak,
            "Dedicated": streak,
            "Unstoppable": streak,
            "Level Up!": topbar["level"],
            "Scholar": topbar["level"],
            "XP Collector": topbar["exp"],
            "Pet Lover": len(self.pm.get_owned_pets()),
            "Night Lover": 1 if settings_manager.load().get("used_dark_mode", False) else 0,
        }

