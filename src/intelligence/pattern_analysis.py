from datetime import datetime
import json
import os

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

try:
    from src.intelligence.database import get_database
except ImportError:
    from database import get_database


MIN_SESSIONS_REQUIRED = 10
ANALYSIS_UPDATE_INTERVAL = 3  # Re-analyze every N new sessions after MIN_SESSIONS_REQUIRED

_TIME_BUCKETS = ("morning", "afternoon", "evening", "night")
_DURATION_BUCKETS = ("short", "medium", "long", "marathon")

DISTRACTION_COLUMNS = {
    "phone_distractions":     "Phone",
    "look_away_distractions": "Looking Away",
    "left_desk_distractions": "Left Desk",
    "app_distractions":       "App Switch",
    "idle_distractions":      "Idle",
}

_DISTRACTION_TIME_COLS = {
    "look_away_distractions": "look_away_time",
    "left_desk_distractions": "time_away",
}

# Base features always present; distraction features are filtered dynamically
_ML_BASE_FEATURES = ["hour", "day_of_week", "duration"]
_ML_DISTRACTION_FEATURES = list(DISTRACTION_COLUMNS.keys())

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
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _classify_duration(duration_seconds: int) -> str:
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
    return round(sum(values) / len(values), 1) if values else None


def _format_hour(hour_24: int) -> str:
    am_pm = "AM" if hour_24 < 12 else "PM"
    h12 = hour_24 % 12 or 12
    return f"{h12} {am_pm}"


class PatternAnalyzer:

    def __init__(self):
        self.db = get_database()

    def get_session_count(self) -> int:
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE end_time IS NOT NULL"
        )
        row = cursor.fetchone()
        return row["n"] if row else 0

    def has_enough_data(self) -> bool:
        return self.get_session_count() >= MIN_SESSIONS_REQUIRED

    def should_update(self, last_analyzed_count: int) -> bool:
        current = self.get_session_count()
        if current < MIN_SESSIONS_REQUIRED:
            return False
        if last_analyzed_count < MIN_SESSIONS_REQUIRED:
            return True
        return (current - last_analyzed_count) >= ANALYSIS_UPDATE_INTERVAL

    def _fetch_sessions(self) -> list:
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

    def optimal_time_of_day(self, sessions: list) -> dict:
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
        hourly: dict[int, list] = {}

        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["start_time"])
            except (ValueError, TypeError):
                continue
            hourly.setdefault(dt.hour, []).append(s["score"])

        hourly_avg = {
            h: round(sum(v) / len(v), 1)
            for h, v in hourly.items()
            if len(v) >= 2
        }

        peak_hour = max(hourly_avg, key=hourly_avg.get) if hourly_avg else None

        return {"hourly_avg": hourly_avg, "peak_hour": peak_hour}

    def best_day_of_week(self, sessions: list) -> dict:
        _DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        scores_by_day: dict[int, list] = {d: [] for d in range(7)}

        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["start_time"])
            except (ValueError, TypeError):
                continue
            scores_by_day[dt.weekday()].append(s["score"])

        # require at least 2 sessions on a given day before reporting it
        day_avgs = {d: _avg(v) for d, v in scores_by_day.items() if len(v) >= 2}
        best_day  = max(day_avgs, key=day_avgs.get) if day_avgs else None
        worst_day = min(day_avgs, key=day_avgs.get) if day_avgs else None

        return {"day_avgs": day_avgs, "best_day": best_day, "worst_day": worst_day, "day_labels": _DAYS}

    # ------------------------------------------------------------------
    # Machine learning analyses (scikit-learn)
    # ------------------------------------------------------------------

    def _build_feature_matrix(self, sessions: list) -> tuple[np.ndarray, np.ndarray, list[str]]:
        # Only include distraction columns that have at least one tracked event.
        # This keeps ML useful when the user has some tracking types disabled.
        active_distraction_cols = [
            col for col in _ML_DISTRACTION_FEATURES
            if any((s[col] or 0) > 0 for s in sessions)
        ]
        active_features = _ML_BASE_FEATURES + active_distraction_cols

        X, y = [], []
        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["start_time"])
            except (ValueError, TypeError):
                continue

            row = [
                dt.hour,
                dt.weekday(),
                s["duration"] or 0,
            ]
            for col in active_distraction_cols:
                row.append(s[col] or 0)

            X.append(row)
            y.append(s["score"])

        return np.array(X, dtype=float), np.array(y, dtype=float), active_features

    def ml_feature_importance(self, sessions: list) -> dict:
        X, y, active_features = self._build_feature_matrix(sessions)
        if len(X) < 5:
            return {"error": "insufficient_data", "features": [],
                    "r2_score": None, "top_factor": None}

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)

        ranked = sorted(
            zip(active_features, model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )
        features = [
            {
                "feature":        feat,
                "label":          _ML_FEATURE_LABELS[feat],
                "importance":     round(float(imp), 4),
                "importance_pct": round(float(imp) * 100, 1),
            }
            for feat, imp in ranked
        ]

        return {
            "features":   features,
            "r2_score":   round(float(model.score(X, y)), 3),
            "top_factor": features[0]["label"] if features else None,
        }

    def ml_cluster_sessions(self, sessions: list, n_clusters: int = 3) -> dict:
        X, y, active_features = self._build_feature_matrix(sessions)
        if len(X) < n_clusters * 2:
            return {"error": "insufficient_data", "clusters": [],
                    "n_clusters": n_clusters}

        X_with_score = np.column_stack([X, y])

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_with_score)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        n_distraction_cols = len(active_features) - len(_ML_BASE_FEATURES)

        clusters = []
        for i in range(n_clusters):
            mask = labels == i
            cluster_scores = y[mask]
            cluster_X = X[mask]
            cluster_ids = [s["id"] for s, m in zip(sessions, mask) if m]

            avg_score = round(float(cluster_scores.mean()), 1)
            avg_dur   = round(float(cluster_X[:, 2].mean()) / 60, 1)   # col 2 = duration → minutes
            avg_hour  = int(round(float(cluster_X[:, 0].mean())))       # col 0 = hour
            # distraction columns start at index 3
            avg_distractions = (
                round(float(cluster_X[:, 3:].sum(axis=1).mean()), 1)
                if n_distraction_cols > 0 else 0.0
            )

            if avg_score >= 85:
                label = "High Focus"
            elif avg_score >= 70:
                label = "Moderate Focus"
            else:
                label = "Needs Improvement"

            clusters.append({
                "cluster_id":       i,
                "label":            label,
                "session_count":    int(mask.sum()),
                "avg_score":        avg_score,
                "avg_duration_min": avg_dur,
                "avg_hour":         avg_hour,
                "avg_distractions": avg_distractions,
                "session_ids":      cluster_ids,
            })

        clusters.sort(key=lambda c: c["avg_score"], reverse=True)
        return {"clusters": clusters, "n_clusters": n_clusters}

    def ml_forecast_trend(self, sessions: list) -> dict:
        _, y, _ = self._build_feature_matrix(sessions)
        if len(y) < 3:
            return {"error": "insufficient_data", "direction": None,
                    "predicted_next_5": []}

        X_idx = np.arange(len(y)).reshape(-1, 1)
        model = LinearRegression()
        model.fit(X_idx, y)

        slope = round(float(model.coef_[0]), 2)
        r2    = round(float(model.score(X_idx, y)), 3)

        future = np.arange(len(y), len(y) + 5).reshape(-1, 1)
        predictions = [
            round(max(0, min(100, float(p))), 1)
            for p in model.predict(future)
        ]

        if slope > 0.5:
            direction = "improving"
        elif slope < -0.5:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "slope":             slope,
            "r2_score":          r2,
            "direction":         direction,
            "predicted_next_5":  predictions,
            "points_per_session": slope,
        }

    # ------------------------------------------------------------------
    # Insight generation
    # ------------------------------------------------------------------

    def generate_insights(self, analysis: dict) -> list:
        insights = []

        # --- rule-based insights ---

        # time of day
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

        # session length
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

        # most frequent distraction
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

        # most impactful distraction (skip if same as most frequent)
        most_imp = dist.get("most_impactful")
        if most_imp and most_imp != most_freq:
            insights.append(f"{most_imp} costs you the most time overall.")

        # trend
        trend_data = analysis.get("trend", {})
        trend      = trend_data.get("trend")
        delta      = trend_data.get("delta", 0)
        recent_avg = trend_data.get("recent_avg")
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

        # peak hour
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

        # --- ML-derived insights ---

        # feature importance: which factor drives score most
        fi = analysis.get("ml_feature_importance", {})
        fi_features = fi.get("features", [])
        if fi_features and not fi.get("error"):
            top_feat = fi_features[0]
            top_pct  = top_feat["importance_pct"]
            top_lbl  = top_feat["label"]
            if top_feat["feature"] in ("hour", "day_of_week"):
                insights.append(
                    f"When you study matters more than distractions — "
                    f"{top_lbl} accounts for {top_pct:.0f}% of your score."
                )
            elif top_feat["feature"] == "duration":
                insights.append(
                    f"Session length is your biggest performance driver ({top_pct:.0f}% impact). "
                    "Experiment with different durations."
                )
            else:
                insights.append(
                    f"{top_lbl} is your #1 score factor ({top_pct:.0f}% impact). "
                    "Reducing it should give you the biggest gains."
                )

        # forecast: projected trajectory
        forecast = analysis.get("ml_forecast", {})
        if forecast and not forecast.get("error"):
            direction = forecast.get("direction")
            slope     = abs(forecast.get("slope", 0))
            preds     = forecast.get("predicted_next_5", [])
            if direction == "improving" and preds:
                insights.append(
                    f"You're on a roll — improving at +{slope:.1f} pts/session. "
                    f"Projected score in 5 sessions: {preds[-1]:.0f}."
                )
            elif direction == "declining" and preds:
                insights.append(
                    f"Your scores are sliding ~{slope:.1f} pts/session. "
                    f"If this continues, you'll be at {preds[-1]:.0f} in 5 sessions."
                )

        # clustering: describe the best session profile
        cl_data  = analysis.get("ml_clusters", {})
        clusters = cl_data.get("clusters", [])
        if clusters and not cl_data.get("error") and clusters[0]["session_count"] >= 2:
            best    = clusters[0]  # sorted descending by avg_score
            period  = _classify_time_of_day(best["avg_hour"])
            dur_min = best["avg_duration_min"]
            if dur_min < 30:
                dur_label = "short (< 30 min)"
            elif dur_min < 60:
                dur_label = "medium (30–60 min)"
            elif dur_min < 90:
                dur_label = "long (60–90 min)"
            else:
                dur_label = "marathon (90+ min)"
            insights.append(
                f"Your best sessions ({best['label']}, avg {best['avg_score']:.0f}) "
                f"are typically {period}, {dur_label}, "
                f"with {best['avg_distractions']:.1f} avg distractions."
            )

        # day of week: strongest vs weakest day
        dow        = analysis.get("day_of_week", {})
        day_avgs   = dow.get("day_avgs", {})
        day_labels = dow.get("day_labels", [])
        best_day   = dow.get("best_day")
        worst_day  = dow.get("worst_day")
        if best_day is not None and len(day_avgs) >= 2 and best_day != worst_day:
            best_score  = day_avgs[best_day]
            worst_score = day_avgs[worst_day]
            if (best_score - worst_score) >= 5:
                insights.append(
                    f"{day_labels[best_day]} is your strongest study day (avg {best_score:.0f}). "
                    f"{day_labels[worst_day]} tends to be rougher (avg {worst_score:.0f}) — "
                    "consider lighter sessions then."
                )
            else:
                insights.append(
                    f"You perform best on {day_labels[best_day]} (avg {best_score:.0f})."
                )

        # consistency: score standard deviation
        scores = trend_data.get("scores", [])
        if len(scores) >= 5:
            mean     = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std      = round(variance ** 0.5, 1)
            if std >= 15:
                insights.append(
                    f"Your scores are quite variable (±{std:.0f} pts). "
                    "More consistent sessions could raise your floor."
                )
            elif std <= 7:
                insights.append(
                    f"Your scores are very consistent (±{std:.0f} pts). "
                    "You know what works — now push the ceiling."
                )

        return insights

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def analyze(self) -> dict | None:
        if not self.has_enough_data():
            return None

        sessions = self._fetch_sessions()

        result = {
            "session_count":         len(sessions),
            "time_of_day":           self.optimal_time_of_day(sessions),
            "session_length":        self.optimal_session_length(sessions),
            "distractions":          self.top_distractions(sessions),
            "trend":                 self.focus_trend(sessions),
            "peak_focus":            self.peak_focus_hours(sessions),
            "day_of_week":           self.best_day_of_week(sessions),
            "ml_feature_importance": self.ml_feature_importance(sessions),
            "ml_clusters":           self.ml_cluster_sessions(sessions),
            "ml_forecast":           self.ml_forecast_trend(sessions),
        }
        result["insights"] = self.generate_insights(result)

        return result

    # ------------------------------------------------------------------
    # Markdown report generation
    # ------------------------------------------------------------------

    def _fetch_session_events(self, session_id: int) -> list:
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT event_type, timestamp, duration
            FROM events
            WHERE session_id = ?
            ORDER BY timestamp ASC
        ''', (session_id,))
        return cursor.fetchall()

    def generate_session_report(self, session_id: int, output_path: str = None) -> str | None:
        """Generate a per-session distraction summary as a JSON file."""
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT id, start_time, end_time, duration, focused_time,
                   phone_distractions, look_away_distractions,
                   left_desk_distractions, app_distractions, idle_distractions,
                   distraction_time
            FROM sessions
            WHERE id = ? AND end_time IS NOT NULL
        ''', (session_id,))
        session = cursor.fetchone()
        if session is None:
            return None

        events = self._fetch_session_events(session_id)

        # Count and accumulate per-event-type durations from the events table
        event_counts: dict[str, int] = {}
        event_durations: dict[str, list[int]] = {}
        for ev in events:
            etype = ev["event_type"]
            dur   = ev["duration"] or 0
            event_counts[etype]    = event_counts.get(etype, 0) + 1
            event_durations.setdefault(etype, []).append(dur)

        duration         = session["duration"] or 0
        distraction_time = session["distraction_time"] or 0
        focused_time     = max(0, duration - distraction_time)

        distraction_keys = [
            "phone_distraction",
            "look_away_distraction",
            "left_desk_distraction",
            "app_distraction",
            "idle_distraction",
        ]
        # Fallback: build counts from session columns when events table has nothing
        if not event_counts:
            col_to_dist_col = {
                "phone_distraction":     "phone_distractions",
                "look_away_distraction": "look_away_distractions",
                "left_desk_distraction": "left_desk_distractions",
                "app_distraction":       "app_distractions",
                "idle_distraction":      "idle_distractions",
            }
            for key, db_col in col_to_dist_col.items():
                cnt = session[db_col] or 0
                if cnt > 0:
                    event_counts[key] = cnt

        if output_path is None:
            output_path = f"session_{session_id}_report.json"

        report = {
            "generated_at": datetime.now().isoformat(),
            "session_id": session_id,
            "overview": {
                "start_time":           session["start_time"],
                "end_time":             session["end_time"],
                "duration_seconds":     duration,
                "duration_minutes":     round(duration / 60, 1),
                "focused_time_seconds": focused_time,
                "focused_time_minutes": round(focused_time / 60, 1),
                "distraction_time_seconds": distraction_time,
                "distraction_time_minutes": round(distraction_time / 60, 1),
            },
            "distractions": {
                key: {
                    "count":              event_counts.get(key, 0),
                    "event_durations_seconds": event_durations.get(key, []),
                }
                for key in distraction_keys
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return os.path.abspath(output_path)

    def generate_insights_report(self, output_path: str = None,
                                  last_analyzed_count: int = 0) -> str | None:
        """Generate the rolling insights report as a JSON file."""
        if not self.should_update(last_analyzed_count):
            return None
        analysis = self.analyze()
        if analysis is None:
            return None

        if output_path is None:
            output_path = "study_insights_report.json"

        sessions = self._fetch_sessions()
        first_date = sessions[0]["start_time"][:10] if sessions else None
        last_date  = sessions[-1]["start_time"][:10] if sessions else None

        trend_data = analysis.get("trend", {})
        forecast   = analysis.get("ml_forecast", {})
        fi         = analysis.get("ml_feature_importance", {})
        cl         = analysis.get("ml_clusters", {})
        tod        = analysis.get("time_of_day", {})
        sl         = analysis.get("session_length", {})
        dist       = analysis.get("distractions", {})

        report = {
            "generated_at":    datetime.now().isoformat(),
            "session_count":   analysis["session_count"],
            "date_range": {
                "first": first_date,
                "last":  last_date,
            },
            "summary": {
                "overall_avg_score": trend_data.get("overall_avg"),
                "score_trajectory": {
                    "direction":       forecast.get("direction"),
                    "slope_per_session": forecast.get("slope"),
                },
            },
            "insights": analysis.get("insights", []),
            "time_of_day": {
                "best_period": tod.get("best_period"),
                "buckets": tod.get("buckets", {}),
            },
            "session_length": {
                "best_length": sl.get("best_length"),
                "buckets": sl.get("buckets", {}),
            },
            "distractions": {
                "most_frequent":  dist.get("most_frequent"),
                "most_impactful": dist.get("most_impactful"),
                "total_events":   dist.get("total_events"),
                "ranked_by_count": dist.get("ranked_by_count", []),
            },
            "trend": {
                "trend":       trend_data.get("trend"),
                "delta":       trend_data.get("delta"),
                "recent_avg":  trend_data.get("recent_avg"),
                "overall_avg": trend_data.get("overall_avg"),
                "rolling_avg": trend_data.get("rolling_avg", []),
            },
            "peak_focus": analysis.get("peak_focus", {}),
            "ml_feature_importance": {
                "r2_score":   fi.get("r2_score"),
                "top_factor": fi.get("top_factor"),
                "features":   fi.get("features", []),
            },
            "ml_clusters": {
                "n_clusters": cl.get("n_clusters"),
                "clusters":   cl.get("clusters", []),
            },
            "ml_forecast": {
                "direction":         forecast.get("direction"),
                "slope":             forecast.get("slope"),
                "r2_score":          forecast.get("r2_score"),
                "predicted_next_5":  forecast.get("predicted_next_5", []),
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return os.path.abspath(output_path)
