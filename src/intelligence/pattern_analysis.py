"""
Pattern Analysis Module for StudyWidgetApp.

Analyzes historical session data to surface actionable insights:
  - Best time of day to study (average focus score per time-of-day bucket)
  - Optimal session length (average score by duration bracket)
  - Dominant distractions (ranked by frequency and total time lost)
  - Focus trend (rolling score average showing improvement or decline)
  - Peak focus hour (the specific hour correlating with best scores)
  - Human-readable insight strings for display in the UI

Minimum 10 completed sessions required before analysis is generated.
After that threshold is met, results are meaningful to refresh every 3 sessions.
"""

from datetime import datetime
from src.intelligence.database import get_database


MIN_SESSIONS_REQUIRED = 10
ANALYSIS_UPDATE_INTERVAL = 3  # Re-analyze every N new sessions after MIN_SESSIONS_REQUIRED

# Time-of-day buckets mapped to their hour ranges (24h clock)
# "night" wraps midnight: hours >= 21 or < 6
_TIME_BUCKETS = ("morning", "afternoon", "evening", "night")

# Session duration brackets (labels in display order)
_DURATION_BUCKETS = ("short", "medium", "long", "marathon")

# DB column name → human-readable label for each distraction type
DISTRACTION_COLUMNS = {
    "phone_distractions":     "Phone",
    "look_away_distractions": "Looking Away",
    "left_desk_distractions": "Left Desk",
    "app_distractions":       "App Switch",
    "idle_distractions":      "Idle",
}

# Distraction columns that have a corresponding cumulative time column in sessions
_DISTRACTION_TIME_COLS = {
    "look_away_distractions": "look_away_time",
    "left_desk_distractions": "time_away",
}


def _classify_time_of_day(hour: int) -> str:
    """Maps a 24-h hour value to a named time-of-day bucket."""
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _classify_duration(duration_seconds: int) -> str:
    """Maps a session duration in seconds to a named bracket."""
    minutes = duration_seconds / 60
    if minutes < 30:
        return "short"
    elif minutes < 60:
        return "medium"
    elif minutes < 90:
        return "long"
    else:
        return "marathon"


def _avg(values: list) -> float | None:
    """Returns the mean of a non-empty list, or None if the list is empty."""
    return round(sum(values) / len(values), 1) if values else None


def _format_hour(hour_24: int) -> str:
    """Converts a 24-h integer hour to a human-readable string like '2 PM'."""
    am_pm = "AM" if hour_24 < 12 else "PM"
    h12 = hour_24 % 12 or 12
    return f"{h12} {am_pm}"


class PatternAnalyzer:
    """
    Reads completed sessions from the database and computes focus patterns.

    All sub-analyses receive the pre-fetched session list so the DB is queried
    only once per analyze() call.

    Typical usage:
        analyzer = PatternAnalyzer()
        if analyzer.has_enough_data():
            results = analyzer.analyze()
            for insight in results["insights"]:
                print(insight)
    """

    def __init__(self):
        self.db = get_database()

    # ------------------------------------------------------------------
    # Data-availability helpers
    # ------------------------------------------------------------------

    def get_session_count(self) -> int:
        """Returns the number of fully completed sessions stored in the DB."""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE end_time IS NOT NULL"
        )
        row = cursor.fetchone()
        return row["n"] if row else 0

    def has_enough_data(self) -> bool:
        """Returns True when at least MIN_SESSIONS_REQUIRED sessions are complete."""
        return self.get_session_count() >= MIN_SESSIONS_REQUIRED

    def should_update(self, last_analyzed_count: int) -> bool:
        """
        Returns True if enough new sessions have arrived since the last analysis run.

        Pass the session count that was current when analyze() was last called
        (or 0 on the very first call). Returns True once MIN_SESSIONS_REQUIRED
        sessions exist, then again every ANALYSIS_UPDATE_INTERVAL sessions.
        """
        current = self.get_session_count()
        if current < MIN_SESSIONS_REQUIRED:
            return False
        if last_analyzed_count < MIN_SESSIONS_REQUIRED:
            return True  # First eligible analysis
        return (current - last_analyzed_count) >= ANALYSIS_UPDATE_INTERVAL

    def _fetch_sessions(self) -> list:
        """Fetches all completed sessions ordered by start time ascending."""
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT
                id, start_time, end_time, duration, focused_time,
                score, focus_percentage, distraction_time,
                phone_distractions, look_away_distractions,
                left_desk_distractions, app_distractions, idle_distractions,
                time_away, look_away_time, events
            FROM sessions
            WHERE end_time IS NOT NULL
            ORDER BY start_time ASC
        ''')
        return cursor.fetchall()

    # ------------------------------------------------------------------
    # Sub-analyses (each accepts the pre-fetched sessions list)
    # ------------------------------------------------------------------

    def optimal_time_of_day(self, sessions: list) -> dict:
        """
        Groups sessions by time-of-day bucket and computes average scores.

        Buckets: morning (06–11), afternoon (12–16), evening (17–20), night (21–05).

        Returns:
            {
                "buckets": {
                    "morning":   {"count": N, "avg_score": X, "avg_focus_pct": Y},
                    "afternoon": {...},
                    "evening":   {...},
                    "night":     {...},
                },
                "best_period": "morning",  # highest avg_score; None if no sessions
            }
        """
        scores_by_period = {b: [] for b in _TIME_BUCKETS}
        focus_by_period  = {b: [] for b in _TIME_BUCKETS}

        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["start_time"])
            except (ValueError, TypeError):
                continue
            period = _classify_time_of_day(dt.hour)
            scores_by_period[period].append(s["score"])
            focus_by_period[period].append(s["focus_percentage"] or 0)

        buckets = {}
        for period in _TIME_BUCKETS:
            s_list = scores_by_period[period]
            f_list = focus_by_period[period]
            buckets[period] = {
                "count":         len(s_list),
                "avg_score":     _avg(s_list),
                "avg_focus_pct": _avg(f_list),
            }

        candidates = [(p, d["avg_score"]) for p, d in buckets.items() if d["avg_score"] is not None]
        best_period = max(candidates, key=lambda x: x[1])[0] if candidates else None

        return {"buckets": buckets, "best_period": best_period}

    def optimal_session_length(self, sessions: list) -> dict:
        """
        Groups sessions by duration bracket and computes average scores.

        Brackets: short (<30 min), medium (30–59 min), long (60–89 min), marathon (90+ min).

        Returns:
            {
                "buckets": {
                    "short":    {"count": N, "avg_score": X, "avg_focus_pct": Y},
                    "medium":   {...},
                    "long":     {...},
                    "marathon": {...},
                },
                "best_length": "medium",  # highest avg_score; None if no sessions
            }
        """
        scores_by_bracket = {b: [] for b in _DURATION_BUCKETS}
        focus_by_bracket  = {b: [] for b in _DURATION_BUCKETS}

        for s in sessions:
            bracket = _classify_duration(s["duration"] or 0)
            scores_by_bracket[bracket].append(s["score"])
            focus_by_bracket[bracket].append(s["focus_percentage"] or 0)

        buckets = {}
        for bracket in _DURATION_BUCKETS:
            s_list = scores_by_bracket[bracket]
            f_list = focus_by_bracket[bracket]
            buckets[bracket] = {
                "count":         len(s_list),
                "avg_score":     _avg(s_list),
                "avg_focus_pct": _avg(f_list),
            }

        candidates = [(b, d["avg_score"]) for b, d in buckets.items() if d["avg_score"] is not None]
        best_length = max(candidates, key=lambda x: x[1])[0] if candidates else None

        return {"buckets": buckets, "best_length": best_length}

    def top_distractions(self, sessions: list) -> dict:
        """
        Aggregates all distraction counts and times across sessions.

        Returns:
            {
                "ranked_by_count": [
                    {
                        "type":              "Phone",
                        "column":            "phone_distractions",
                        "total_events":      N,
                        "pct_of_all_events": X,
                    },
                    ...  # sorted high → low by total_events
                ],
                "most_frequent":  "Phone",         # label of highest-count type (None if no events)
                "most_impactful": "Looking Away",  # label of type with most cumulative time lost
                "total_events":   N,
            }
        """
        event_totals = {col: 0 for col in DISTRACTION_COLUMNS}
        time_totals  = {col: 0 for col in DISTRACTION_COLUMNS}

        for s in sessions:
            for col in DISTRACTION_COLUMNS:
                event_totals[col] += s[col] or 0
            for col, time_col in _DISTRACTION_TIME_COLS.items():
                time_totals[col] += s[time_col] or 0

        total_events = sum(event_totals.values())

        ranked = sorted(
            DISTRACTION_COLUMNS.items(),
            key=lambda item: event_totals[item[0]],
            reverse=True,
        )

        ranked_list = []
        for col, label in ranked:
            count = event_totals[col]
            pct = round((count / total_events) * 100, 1) if total_events > 0 else 0.0
            ranked_list.append({
                "type":              label,
                "column":            col,
                "total_events":      count,
                "pct_of_all_events": pct,
            })

        most_frequent = ranked_list[0]["type"] if (ranked_list and ranked_list[0]["total_events"] > 0) else None

        # Most impactful = type with highest total time lost (only types with a time column)
        time_candidates = {col: t for col, t in time_totals.items() if t > 0}
        if time_candidates:
            top_time_col = max(time_candidates, key=time_candidates.get)
            most_impactful = DISTRACTION_COLUMNS[top_time_col]
        else:
            most_impactful = None

        return {
            "ranked_by_count": ranked_list,
            "most_frequent":   most_frequent,
            "most_impactful":  most_impactful,
            "total_events":    total_events,
        }

    def focus_trend(self, sessions: list, window: int = 5) -> dict:
        """
        Computes a rolling average of focus scores to reveal improvement or decline.

        A trend is "improving" if the recent window average is >= 3 pts above
        the overall average, "declining" if >= 3 pts below, otherwise "stable".

        Returns:
            {
                "rolling_avg": [float, ...],  # one entry per session
                "recent_avg":  X,             # avg of last `window` sessions
                "overall_avg": Y,
                "trend":       "improving" | "declining" | "stable",
                "delta":       +N,            # recent_avg - overall_avg
            }
        """
        if not sessions:
            return {
                "scores":      [],
                "rolling_avg": [],
                "recent_avg":  None,
                "overall_avg": None,
                "trend":       "insufficient_data",
                "delta":       0,
            }

        scores = [s["score"] for s in sessions]
        n = len(scores)

        rolling = []
        for i in range(n):
            chunk = scores[max(0, i - window + 1): i + 1]
            rolling.append(round(sum(chunk) / len(chunk), 1))

        overall_avg  = round(sum(scores) / n, 1)
        recent_slice = scores[-window:] if n >= window else scores
        recent_avg   = round(sum(recent_slice) / len(recent_slice), 1)

        delta = round(recent_avg - overall_avg, 1)
        if delta >= 3:
            trend = "improving"
        elif delta <= -3:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "scores":      scores,
            "rolling_avg": rolling,
            "recent_avg":  recent_avg,
            "overall_avg": overall_avg,
            "trend":       trend,
            "delta":       delta,
        }

    def peak_focus_hours(self, sessions: list) -> dict:
        """
        Identifies which hour of the day correlates with the highest average score.

        Only hours with at least 2 sessions are considered to avoid single-session noise.

        Returns:
            {
                "hourly_avg": {14: 88.5, 9: 82.0, ...},  # populated hours only
                "peak_hour":  14,                          # best hour (None if no data)
            }
        """
        hourly: dict[int, list] = {}

        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["start_time"])
            except (ValueError, TypeError):
                continue
            hourly.setdefault(dt.hour, []).append(s["score"])

        # Require at least 2 sessions per hour to report that hour
        hourly_avg = {
            h: round(sum(v) / len(v), 1)
            for h, v in hourly.items()
            if len(v) >= 2
        }

        peak_hour = max(hourly_avg, key=hourly_avg.get) if hourly_avg else None

        return {"hourly_avg": hourly_avg, "peak_hour": peak_hour}

    # ------------------------------------------------------------------
    # Insight generation
    # ------------------------------------------------------------------

    def generate_insights(self, analysis: dict) -> list:
        """
        Converts raw analysis results into concise, human-readable insight strings.

        One insight is generated per category at most. Returns an empty list if no
        meaningful conclusion can be drawn (e.g. all sessions in one bucket).
        """
        insights = []

        # Time of day
        tod = analysis.get("time_of_day", {})
        best_period = tod.get("best_period")
        if best_period:
            bucket = tod.get("buckets", {}).get(best_period, {})
            avg    = bucket.get("avg_score")
            count  = bucket.get("count", 0)
            if avg is not None and count >= 2:
                insights.append(
                    f"You focus best in the {best_period} "
                    f"(avg score {avg:.0f} across {count} sessions)."
                )

        # Session length
        length = analysis.get("session_length", {})
        best_len = length.get("best_length")
        if best_len:
            bucket = length.get("buckets", {}).get(best_len, {})
            avg    = bucket.get("avg_score")
            count  = bucket.get("count", 0)
            labels = {
                "short":    "under 30 minutes",
                "medium":   "30–60 minutes",
                "long":     "60–90 minutes",
                "marathon": "over 90 minutes",
            }
            if avg is not None and count >= 2:
                insights.append(
                    f"Your sweet spot is {labels.get(best_len, best_len)} sessions "
                    f"(avg score {avg:.0f})."
                )

        # Distractions – most frequent
        dist = analysis.get("distractions", {})
        most_freq = dist.get("most_frequent")
        if most_freq:
            ranked = dist.get("ranked_by_count", [])
            top = next((r for r in ranked if r["type"] == most_freq), None)
            if top and top["total_events"] > 0:
                insights.append(
                    f"{most_freq} is your most frequent distraction "
                    f"({top['total_events']} events, {top['pct_of_all_events']:.0f}% of total)."
                )

        # Distractions – most impactful (only if different from most frequent)
        most_imp = dist.get("most_impactful")
        if most_imp and most_imp != most_freq:
            insights.append(f"{most_imp} costs you the most time overall.")

        # Trend
        trend_data  = analysis.get("trend", {})
        trend       = trend_data.get("trend")
        delta       = trend_data.get("delta", 0)
        recent_avg  = trend_data.get("recent_avg")
        if trend == "improving" and recent_avg is not None:
            insights.append(
                f"Your scores are trending up "
                f"(+{delta:.0f} pts vs your overall average of {trend_data.get('overall_avg', 0):.0f})."
            )
        elif trend == "declining" and recent_avg is not None:
            insights.append(
                f"Your scores have dipped recently "
                f"({delta:.0f} pts vs your overall average). "
                "Try a shorter session or a different time of day."
            )

        # Peak hour
        peak = analysis.get("peak_focus", {})
        peak_hour = peak.get("peak_hour")
        if peak_hour is not None:
            peak_score = peak.get("hourly_avg", {}).get(peak_hour)
            hour_str   = _format_hour(peak_hour)
            if peak_score is not None:
                insights.append(
                    f"Your sharpest hour is around {hour_str} "
                    f"(avg score {peak_score:.0f})."
                )

        return insights

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def analyze(self) -> dict | None:
        """
        Runs all pattern analyses and returns a combined results dict.

        Returns None if fewer than MIN_SESSIONS_REQUIRED completed sessions exist.

        Return structure:
            {
                "session_count":  N,
                "time_of_day":    { "buckets": {...}, "best_period": str },
                "session_length": { "buckets": {...}, "best_length": str },
                "distractions":   { "ranked_by_count": [...], "most_frequent": str,
                                    "most_impactful": str, "total_events": N },
                "trend":          { "rolling_avg": [...], "recent_avg": X,
                                    "overall_avg": Y, "trend": str, "delta": N },
                "peak_focus":     { "hourly_avg": {...}, "peak_hour": int },
                "insights":       [ str, ... ],
            }
        """
        if not self.has_enough_data():
            return None

        sessions = self._fetch_sessions()

        result = {
            "session_count":  len(sessions),
            "time_of_day":    self.optimal_time_of_day(sessions),
            "session_length": self.optimal_session_length(sessions),
            "distractions":   self.top_distractions(sessions),
            "trend":          self.focus_trend(sessions),
            "peak_focus":     self.peak_focus_hours(sessions),
        }
        result["insights"] = self.generate_insights(result)

        return result
