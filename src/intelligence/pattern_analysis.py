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
import os

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from database import get_database


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

# Feature names used by ML models
_ML_FEATURES = [
    "hour", "day_of_week", "duration",
    "phone_distractions", "look_away_distractions",
    "left_desk_distractions", "app_distractions", "idle_distractions",
]

_ML_FEATURE_LABELS = {
    "hour":                    "Time of Day (Hour)",
    "day_of_week":             "Day of Week",
    "duration":                "Session Duration",
    "phone_distractions":      "Phone Distractions",
    "look_away_distractions":  "Look-Away Distractions",
    "left_desk_distractions":  "Left Desk Distractions",
    "app_distractions":        "App Distractions",
    "idle_distractions":       "Idle Distractions",
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
    # Machine learning analyses (scikit-learn)
    #
    # These methods apply supervised and unsupervised ML models to the
    # same session data used by the rule-based analyses above.  The goal
    # is to surface patterns that simple averages and buckets can miss —
    # for example, which combination of factors best predicts a high
    # score, or whether sessions naturally group into distinct profiles.
    #
    # Models used:
    #   1. Random Forest Regressor  – feature importance (what matters most)
    #   2. K-Means Clustering       – session profile grouping
    #   3. Linear Regression        – score trend forecasting
    # ------------------------------------------------------------------

    def _build_feature_matrix(self, sessions: list) -> tuple[np.ndarray, np.ndarray]:
        """
        Converts session rows into a feature matrix X and target vector y.

        Features per session: hour, day_of_week, duration, and each
        distraction count.  Target: session score.

        This is the shared data-preparation step consumed by every ML
        method.  Each row in X corresponds to one completed session,
        and the column order matches _ML_FEATURES.
        """
        X, y = [], []
        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["start_time"])
            except (ValueError, TypeError):
                continue

            # Build one feature row per session.
            # Columns: [hour, day_of_week, duration, phone, look_away,
            #           left_desk, app, idle]
            X.append([
                dt.hour,                           # 0-23, when the session started
                dt.weekday(),                      # 0=Mon … 6=Sun
                s["duration"] or 0,                # total length in seconds
                s["phone_distractions"] or 0,      # distraction event counts ↓
                s["look_away_distractions"] or 0,
                s["left_desk_distractions"] or 0,
                s["app_distractions"] or 0,
                s["idle_distractions"] or 0,
            ])
            y.append(s["score"])
        return np.array(X, dtype=float), np.array(y, dtype=float)

    # ---- 1. Feature importance (Random Forest) ----------------------

    def ml_feature_importance(self, sessions: list) -> dict:
        """
        Trains a Random Forest regressor to predict focus scores and extracts
        feature importances — revealing which factors most affect performance.

        How it works:
          - A Random Forest is an ensemble of decision trees.  Each tree
            is trained on a random subset of the data and features.
          - After fitting, sklearn exposes `feature_importances_`: the
            average reduction in prediction error each feature provides
            across all trees (Mean Decrease in Impurity).
          - A higher importance % means that feature is a stronger
            driver of whether a session scores well or poorly.

        The R² score (coefficient of determination) indicates how well
        the model fits the data: 1.0 = perfect, 0.0 = no better than
        predicting the mean.  Because we evaluate on training data, a
        high R² is expected — it confirms the model captured the
        patterns, not that it would generalise to new users.

        Requires at least 5 sessions.
        """
        X, y = self._build_feature_matrix(sessions)
        if len(X) < 5:
            return {"error": "insufficient_data", "features": [],
                    "r2_score": None, "top_factor": None}

        # 100 trees gives stable importance estimates while staying fast
        # on small datasets.  random_state pins the result for reproducibility.
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)

        # Pair each feature name with its importance and sort descending
        ranked = sorted(
            zip(_ML_FEATURES, model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )
        features = [
            {
                "feature": feat,                    # internal key (e.g. "phone_distractions")
                "label": _ML_FEATURE_LABELS[feat],  # display name (e.g. "Phone Distractions")
                "importance": round(float(imp), 4),
                "importance_pct": round(float(imp) * 100, 1),
            }
            for feat, imp in ranked
        ]

        return {
            "features": features,
            "r2_score": round(float(model.score(X, y)), 3),
            "top_factor": features[0]["label"] if features else None,
        }

    # ---- 2. Session clustering (K-Means) ----------------------------

    def ml_cluster_sessions(self, sessions: list, n_clusters: int = 3) -> dict:
        """
        Groups sessions into performance clusters using K-Means.

        How it works:
          - Features + score are combined into a single matrix, then
            standardised with StandardScaler (zero mean, unit variance)
            so that no single feature dominates due to scale differences
            (e.g. duration in seconds vs distraction counts).
          - K-Means partitions sessions into `n_clusters` groups by
            minimising within-cluster variance.  Each session is
            assigned to the nearest centroid.
          - Clusters are then labelled by their average score:
                >= 85  →  "High Focus"
                >= 70  →  "Moderate Focus"
                <  70  →  "Needs Improvement"

        Requires at least n_clusters * 2 sessions so each cluster
        can contain a meaningful number of members.
        """
        X, y = self._build_feature_matrix(sessions)
        if len(X) < n_clusters * 2:
            return {"error": "insufficient_data", "clusters": [],
                    "n_clusters": n_clusters}

        # Append score as a clustering feature so sessions are grouped
        # by both their inputs (time, distractions) AND their outcome.
        X_with_score = np.column_stack([X, y])

        # Standardise: K-Means uses Euclidean distance, so features on
        # different scales (duration ~3600 vs distractions ~2) would
        # skew the grouping without normalisation.
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_with_score)

        # n_init=10 runs K-Means 10 times with different centroid seeds
        # and keeps the best result, reducing sensitivity to initialisation.
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        # Build a profile summary for each cluster
        clusters = []
        for i in range(n_clusters):
            mask = labels == i                      # boolean mask for this cluster's sessions
            cluster_scores = y[mask]
            cluster_X = X[mask]
            cluster_ids = [s["id"] for s, m in zip(sessions, mask) if m]

            avg_score = round(float(cluster_scores.mean()), 1)
            avg_dur = round(float(cluster_X[:, 2].mean()) / 60, 1)   # col 2 = duration → minutes
            avg_hour = int(round(float(cluster_X[:, 0].mean())))      # col 0 = hour
            avg_distractions = round(
                float(cluster_X[:, 3:].sum(axis=1).mean()), 1         # cols 3-7 = distraction counts
            )

            # Assign a human-readable label based on cluster quality
            if avg_score >= 85:
                label = "High Focus"
            elif avg_score >= 70:
                label = "Moderate Focus"
            else:
                label = "Needs Improvement"

            clusters.append({
                "cluster_id": i,
                "label": label,
                "session_count": int(mask.sum()),
                "avg_score": avg_score,
                "avg_duration_min": avg_dur,
                "avg_hour": avg_hour,
                "avg_distractions": avg_distractions,
                "session_ids": cluster_ids,
            })

        # Present best-performing cluster first
        clusters.sort(key=lambda c: c["avg_score"], reverse=True)
        return {"clusters": clusters, "n_clusters": n_clusters}

    # ---- 3. Score trend forecasting (Linear Regression) -------------

    def ml_forecast_trend(self, sessions: list) -> dict:
        """
        Fits a linear regression on scores over time to forecast trajectory.

        How it works:
          - X is the session index (0, 1, 2, …), y is the session score.
          - A simple y = slope * x + intercept line is fitted.
          - The slope tells us how many points the score changes per
            session on average:
                slope >  0.5  →  "improving"
                slope < -0.5  →  "declining"
                otherwise     →  "stable"
          - The model then extrapolates 5 sessions into the future,
            clamped to [0, 100].

        R² here reflects how linear the score progression is — a low R²
        doesn't mean the forecast is wrong, just that scores are noisy
        and don't follow a clean trend line.

        Requires at least 3 sessions.
        """
        _, y = self._build_feature_matrix(sessions)
        if len(y) < 3:
            return {"error": "insufficient_data", "direction": None,
                    "predicted_next_5": []}

        # Session index as the sole predictor (simple trend over time)
        X_idx = np.arange(len(y)).reshape(-1, 1)
        model = LinearRegression()
        model.fit(X_idx, y)

        # slope = average score change per session
        slope = round(float(model.coef_[0]), 2)
        r2 = round(float(model.score(X_idx, y)), 3)

        # Project scores for the next 5 hypothetical sessions
        future = np.arange(len(y), len(y) + 5).reshape(-1, 1)
        predictions = [
            round(max(0, min(100, float(p))), 1)  # clamp to valid score range
            for p in model.predict(future)
        ]

        if slope > 0.5:
            direction = "improving"
        elif slope < -0.5:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "slope": slope,
            "r2_score": r2,
            "direction": direction,
            "predicted_next_5": predictions,
            "points_per_session": slope,
        }

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
            "session_count":        len(sessions),
            "time_of_day":          self.optimal_time_of_day(sessions),
            "session_length":       self.optimal_session_length(sessions),
            "distractions":         self.top_distractions(sessions),
            "trend":                self.focus_trend(sessions),
            "peak_focus":           self.peak_focus_hours(sessions),
            "ml_feature_importance": self.ml_feature_importance(sessions),
            "ml_clusters":          self.ml_cluster_sessions(sessions),
            "ml_forecast":          self.ml_forecast_trend(sessions),
        }
        result["insights"] = self.generate_insights(result)

        return result

    # ------------------------------------------------------------------
    # Markdown report generation
    # ------------------------------------------------------------------

    def generate_markdown_report(self, output_path: str = None) -> str | None:
        """
        Runs the full analysis and writes a formatted Markdown report.

        Defaults to ``study_insights_report.md`` in the working directory.
        Returns the absolute path written, or None if data is insufficient.
        """
        analysis = self.analyze()
        if analysis is None:
            return None

        if output_path is None:
            output_path = "study_insights_report.md"

        sessions = self._fetch_sessions()
        first_date = sessions[0]["start_time"][:10] if sessions else "N/A"
        last_date  = sessions[-1]["start_time"][:10] if sessions else "N/A"

        lines: list[str] = []
        _a = lines.append

        # ── Header ──────────────────────────────────────────────
        _a("# Study Session Pattern Analysis Report\n")
        _a(f"> Generated on {datetime.now().strftime('%B %d, %Y')} "
           f"| {analysis['session_count']} sessions analyzed\n")
        _a("---\n")

        # ── Summary table ───────────────────────────────────────
        trend_data = analysis.get("trend", {})
        forecast   = analysis.get("ml_forecast", {})
        _a("## Summary\n")
        _a("| Metric | Value |")
        _a("|--------|-------|")
        _a(f"| Sessions Analyzed | {analysis['session_count']} |")
        _a(f"| Date Range | {first_date} to {last_date} |")
        overall_avg = trend_data.get("overall_avg", "N/A")
        _a(f"| Overall Avg Score | {overall_avg} |")
        if forecast.get("direction"):
            slope = forecast.get("slope", 0)
            sign = "+" if slope >= 0 else ""
            _a(f"| Score Trajectory | {forecast['direction'].title()} "
               f"({sign}{slope} pts/session) |")
        _a("")

        # ── Key Insights ────────────────────────────────────────
        insights = analysis.get("insights", [])
        if insights:
            _a("## Key Insights\n")
            for ins in insights:
                _a(f"- {ins}")
            _a("")

        _a("---\n")

        # ── ML: Feature Importance ──────────────────────────────
        fi = analysis.get("ml_feature_importance", {})
        if fi.get("features"):
            _a("## Machine Learning Analysis\n")
            _a("### What Affects Your Focus Most\n")
            _a("A **Random Forest** model was trained on your session data to "
               "determine which factors have the greatest impact on your "
               "focus score.\n")
            r2 = fi.get("r2_score")
            if r2 is not None:
                _a(f"*Model fit: R\u00b2 = {r2}*\n")
            _a("| Rank | Factor | Importance |")
            _a("|------|--------|-----------|")
            for rank, feat in enumerate(fi["features"], 1):
                _a(f"| {rank} | {feat['label']} | {feat['importance_pct']}% |")
            _a("")
            top = fi.get("top_factor")
            if top:
                _a(f"**Takeaway:** *{top}* has the strongest influence "
                   "on your focus score.\n")

        # ── ML: Clusters ────────────────────────────────────────
        cl = analysis.get("ml_clusters", {})
        clusters = cl.get("clusters", [])
        if clusters:
            _a("### Your Session Profiles\n")
            _a(f"K-Means clustering identified **{len(clusters)} distinct "
               "session patterns**:\n")
            icons = {
                "High Focus": "\U0001f7e2",
                "Moderate Focus": "\U0001f7e1",
                "Needs Improvement": "\U0001f534",
            }
            for c in clusters:
                icon = icons.get(c["label"], "\u26aa")
                _a(f"#### {icon} {c['label']} "
                   f"({c['session_count']} sessions)\n")
                _a(f"- **Avg Score:** {c['avg_score']}")
                _a(f"- **Avg Duration:** {c['avg_duration_min']} min")
                _a(f"- **Avg Distractions:** {c['avg_distractions']}")
                _a(f"- **Typical Hour:** {_format_hour(c['avg_hour'])}")
                ids_str = ", ".join(f"#{sid}" for sid in c["session_ids"])
                _a(f"- **Sessions:** {ids_str}")
                _a("")

        # ── ML: Forecast ────────────────────────────────────────
        if forecast.get("direction"):
            _a("### Score Forecast\n")
            _a("Linear regression on your score history:\n")
            slope = forecast.get("slope", 0)
            sign = "+" if slope >= 0 else ""
            _a(f"- **Trajectory:** {forecast['direction'].title()} "
               f"({sign}{slope} pts/session)")
            _a(f"- **Model Confidence:** R\u00b2 = "
               f"{forecast.get('r2_score', 'N/A')}")
            preds = forecast.get("predicted_next_5", [])
            if preds:
                preds_str = ", ".join(str(p) for p in preds)
                _a(f"- **Projected Scores (next 5 sessions):** {preds_str}")
            _a("")

        _a("---\n")

        # ── Detailed: Time of Day ───────────────────────────────
        _a("## Detailed Breakdowns\n")
        tod = analysis.get("time_of_day", {})
        buckets = tod.get("buckets", {})
        if buckets:
            _a("### Performance by Time of Day\n")
            period_labels = {
                "morning":   "Morning (6 AM \u2013 12 PM)",
                "afternoon": "Afternoon (12 PM \u2013 5 PM)",
                "evening":   "Evening (5 PM \u2013 9 PM)",
                "night":     "Night (9 PM \u2013 6 AM)",
            }
            _a("| Period | Sessions | Avg Score | Avg Focus % |")
            _a("|--------|----------|-----------|-------------|")
            best = tod.get("best_period")
            for period in _TIME_BUCKETS:
                b = buckets.get(period, {})
                count = b.get("count", 0)
                avg_s = b.get("avg_score")
                avg_f = b.get("avg_focus_pct")
                label = period_labels.get(period, period)
                marker = " \u2b50" if period == best else ""
                score_str = f"{avg_s}" if avg_s is not None else "\u2014"
                focus_str = f"{avg_f}%" if avg_f is not None else "\u2014"
                _a(f"| {label}{marker} | {count} | {score_str} | {focus_str} |")
            _a("")

        # ── Detailed: Session Length ────────────────────────────
        sl = analysis.get("session_length", {})
        sl_buckets = sl.get("buckets", {})
        if sl_buckets:
            _a("### Performance by Session Length\n")
            dur_labels = {
                "short":    "Short (< 30 min)",
                "medium":   "Medium (30 \u2013 60 min)",
                "long":     "Long (60 \u2013 90 min)",
                "marathon": "Marathon (90+ min)",
            }
            _a("| Duration | Sessions | Avg Score | Avg Focus % |")
            _a("|----------|----------|-----------|-------------|")
            best_len = sl.get("best_length")
            for bracket in _DURATION_BUCKETS:
                b = sl_buckets.get(bracket, {})
                count = b.get("count", 0)
                avg_s = b.get("avg_score")
                avg_f = b.get("avg_focus_pct")
                label = dur_labels.get(bracket, bracket)
                marker = " \u2b50" if bracket == best_len else ""
                score_str = f"{avg_s}" if avg_s is not None else "\u2014"
                focus_str = f"{avg_f}%" if avg_f is not None else "\u2014"
                _a(f"| {label}{marker} | {count} | {score_str} | "
                   f"{focus_str} |")
            _a("")

        # ── Detailed: Distractions ──────────────────────────────
        dist = analysis.get("distractions", {})
        ranked = dist.get("ranked_by_count", [])
        if ranked:
            _a("### Distraction Breakdown\n")
            _a("| Type | Events | % of Total |")
            _a("|------|--------|-----------|")
            for r in ranked:
                _a(f"| {r['type']} | {r['total_events']} "
                   f"| {r['pct_of_all_events']}% |")
            _a("")
            if dist.get("most_impactful"):
                _a(f"**Most time lost to:** {dist['most_impactful']}\n")

        # ── Detailed: Focus Trend ───────────────────────────────
        if (trend_data.get("trend")
                and trend_data["trend"] != "insufficient_data"):
            _a("### Focus Trend\n")
            _a(f"- **Recent Average (last 5):** "
               f"{trend_data.get('recent_avg', 'N/A')}")
            _a(f"- **Overall Average:** "
               f"{trend_data.get('overall_avg', 'N/A')}")
            delta = trend_data.get("delta", 0)
            sign = "+" if delta >= 0 else ""
            _a(f"- **Trend:** {trend_data['trend'].title()} "
               f"({sign}{delta} pts)")
            _a("")

        _a("---\n")
        _a("*Report generated by StudyWidgetApp Pattern Analyzer*\n")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return os.path.abspath(output_path)