import sqlite3
from src.intelligence.database import Database
from src.intelligence.pattern_analysis import PatternAnalyzer

def _row_to_dict(row):
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

class DatabaseReader:
    def __init__(self):
        self.db = Database()._get_connection()

    # get user info and stats
    def get_user_info(self):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT avg_focus_time, current_pet from user_stats where id = 1
        ''')
        return _row_to_dict(cursor.fetchone())

    def get_topbar_data(self):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT level, coins, exp from user_stats where id = 1
        ''')
        return _row_to_dict(cursor.fetchone())

    # get session dates
    def get_session_dates(self):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT start_time FROM sessions WHERE end_time IS NOT NULL ORDER BY start_time ASC
        ''')
        # TODO: Convert start_time if not already in ISO 8601 format
        return [_row_to_dict(row) for row in cursor.fetchall()]

    # get previous session data
    def get_previous_session_data(self):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT score, points_earned, coins_earned, focus_percentage, events,
                   focused_time, distraction_time, duration
            FROM sessions WHERE end_time IS NOT NULL ORDER BY id DESC LIMIT 1
        ''')
        return _row_to_dict(cursor.fetchone())

    def get_recent_scores(self, limit=10):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT score FROM sessions
            WHERE end_time IS NOT NULL
            ORDER BY id DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        return [row['score'] for row in reversed(rows)]

    def get_scores_by_date(self):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT DATE(start_time) AS session_date, AVG(score) AS avg_score
            FROM sessions
            WHERE end_time IS NOT NULL
            GROUP BY DATE(start_time)
        ''')
        return {row['session_date']: row['avg_score'] for row in cursor.fetchall()}

    def load_dashboard_data(self):
        user_info = self.get_user_info()
        session_dates = self.get_session_dates()
        previous_session_data = self.get_previous_session_data()
        recent_scores = self.get_recent_scores()
        scores_by_date = self.get_scores_by_date()
        return {
            "user_info": user_info if user_info else {},
            "session_dates": session_dates if session_dates else [],
            "previous_session_data": previous_session_data,
            "recent_scores": recent_scores,
            "scores_by_date": scores_by_date,
        }

    def get_session_analytics(self):
        # get session analytics
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT
                COALESCE(SUM(focused_time), 0)       AS lifetime_focus_seconds,
                COUNT(*)                             AS total_sessions,
                COALESCE(AVG(focused_time), 0)       AS avg_focus_seconds,
                COALESCE(SUM(distraction_time), 0)   AS total_distraction_seconds,
                COALESCE(MAX(focused_time), 0)       AS longest_focus_seconds,
                COALESCE(SUM(points_earned), 0)      AS total_points_from_sessions
            FROM sessions
            WHERE end_time IS NOT NULL
        ''')
        return _row_to_dict(cursor.fetchone())

    def get_pattern_analysis(self):
        analyzer = PatternAnalyzer()
        return analyzer.analyze()

    def load_report_data(self):
        session_analytics = self.get_session_analytics()
        pattern_analysis = self.get_pattern_analysis()
        return {
            "session_analytics": session_analytics if session_analytics else {},
            "pattern_analysis": pattern_analysis,
        }