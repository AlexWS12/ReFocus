import sqlite3
from PySide6.QtCore import QThread, Signal, QObject

from src.intelligence.database import Database


def _row_to_dict(row):
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class _AnalysisWorker(QObject):
    finished = Signal(object)

    def run(self):
        try:
            from src.intelligence.pattern_analysis import PatternAnalyzer
            result = PatternAnalyzer().analyze()
        except Exception:
            result = None
        self.finished.emit(result)


class DatabaseReader(QObject):
    # Emitted on the main thread when a background analysis completes.
    analysis_ready = Signal(object)

    def __init__(self):
        super().__init__()
        self.db = Database()._get_connection()
        self._analysis_cache: dict | None = None
        self._analysis_thread: QThread | None = None
        self._analysis_worker: _AnalysisWorker | None = None
        self._analysis_callbacks: list = []

    # ------------------------------------------------------------------
    # Async pattern analysis — runs ML models on a background thread
    # ------------------------------------------------------------------

    def run_analysis_async(self, callback=None):
        # if a thread is already running, queue the callback for when it finishes
        if self._analysis_thread is not None and self._analysis_thread.isRunning():
            if callback is not None:
                self._analysis_callbacks.append(callback)
            return
        # if we already have a cached result, fire the callback immediately (no new thread)
        if self._analysis_cache is not None and callback is not None:
            try:
                callback(self._analysis_cache)
            except RuntimeError:
                pass
            return
        if callback is not None:
            self._analysis_callbacks.append(callback)
        # give thread self as parent so Qt owns its lifetime — prevents "destroyed while
        # running" crash if the Python reference is GC'd before the thread finishes
        thread = QThread(self)
        worker = _AnalysisWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_analysis_done)
        worker.finished.connect(thread.quit)
        # worker cleanup: use a lambda to clear our reference, then deleteLater
        worker.finished.connect(lambda _: worker.deleteLater())
        self._analysis_thread = thread
        self._analysis_worker = worker  # keep Python reference alive
        thread.start()

    def _on_analysis_done(self, result):
        # called on the main thread via AutoConnection
        self._analysis_cache = result
        self._analysis_thread = None
        self._analysis_worker = None
        callbacks = self._analysis_callbacks[:]
        self._analysis_callbacks.clear()
        self.analysis_ready.emit(result)
        for cb in callbacks:
            try:
                cb(result)
            except RuntimeError:
                pass  # widget was deleted before callback fired

    def get_cached_analysis(self) -> dict | None:
        return self._analysis_cache

    # ------------------------------------------------------------------
    # User / stats queries
    # ------------------------------------------------------------------

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

    def get_session_dates(self):
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT start_time FROM sessions WHERE end_time IS NOT NULL ORDER BY start_time ASC
        ''')
        return [_row_to_dict(row) for row in cursor.fetchall()]

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
        # returns the in-memory cache; callers that need a fresh run
        # should use run_analysis_async() instead
        return self._analysis_cache

    def load_report_data(self):
        session_analytics = self.get_session_analytics()
        return {
            "session_analytics": session_analytics if session_analytics else {},
            "pattern_analysis": self._analysis_cache,
        }
