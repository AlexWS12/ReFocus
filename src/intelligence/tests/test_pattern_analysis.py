"""
Pytest-based tests for PatternAnalyzer, covering both the rule-based
sub-analyses and the three scikit-learn ML methods.

Run with:
    pytest src/intelligence/tests/test_pattern_analysis.py -v

Or directly:
    python src/intelligence/tests/test_pattern_analysis.py
"""

import os
import pytest

import sys

# Ensure both src/intelligence and src/intelligence/tests are importable
# regardless of how pytest was invoked (via pyproject.toml pythonpath or
# directly with `python test_pattern_analysis.py`).
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_INTELLIGENCE_DIR = os.path.normpath(os.path.join(_TESTS_DIR, ".."))
for _p in (_INTELLIGENCE_DIR, _TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from database import Database
from pattern_analysis import PatternAnalyzer, MIN_SESSIONS_REQUIRED
from generate_mock_db import create_mock_database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analyzer_empty(tmp_path):
    """PatternAnalyzer backed by a fresh empty database (0 sessions)."""
    db = Database(db_path=str(tmp_path / "empty.db"))
    analyzer = PatternAnalyzer()
    analyzer.db = db._get_connection()
    yield analyzer
    db.close()


@pytest.fixture
def analyzer_mock(tmp_path):
    """PatternAnalyzer backed by the full 20-session mock database."""
    db_path = str(tmp_path / "mock.db")
    create_mock_database(db_path)
    db = Database(db_path=db_path)
    analyzer = PatternAnalyzer()
    analyzer.db = db._get_connection()
    yield analyzer
    db.close()


@pytest.fixture
def full_analysis(analyzer_mock):
    """Pre-computed analyze() result from the mock database."""
    return analyzer_mock.analyze()


# ---------------------------------------------------------------------------
# Data-availability guards
# ---------------------------------------------------------------------------

class TestDataAvailability:

    def test_empty_db_has_no_data(self, analyzer_empty):
        assert analyzer_empty.get_session_count() == 0
        assert not analyzer_empty.has_enough_data()

    def test_empty_db_analyze_returns_none(self, analyzer_empty):
        assert analyzer_empty.analyze() is None

    def test_mock_db_has_enough_data(self, analyzer_mock):
        assert analyzer_mock.get_session_count() >= MIN_SESSIONS_REQUIRED
        assert analyzer_mock.has_enough_data()

    def test_should_update_logic(self, analyzer_mock):
        count = analyzer_mock.get_session_count()
        # Last-analyzed count below threshold → should update
        assert analyzer_mock.should_update(0)
        # Already at current count → should not update yet
        assert not analyzer_mock.should_update(count)


# ---------------------------------------------------------------------------
# analyze() return structure
# ---------------------------------------------------------------------------

class TestAnalyzeStructure:

    def test_returns_all_keys(self, full_analysis):
        expected = {
            "session_count", "time_of_day", "session_length",
            "distractions", "trend", "peak_focus",
            "ml_feature_importance", "ml_clusters", "ml_forecast",
            "insights",
        }
        assert expected.issubset(full_analysis.keys())

    def test_session_count_matches_mock(self, full_analysis):
        assert full_analysis["session_count"] == 20

    def test_insights_is_nonempty_list(self, full_analysis):
        assert isinstance(full_analysis["insights"], list)
        assert len(full_analysis["insights"]) > 0


# ---------------------------------------------------------------------------
# Rule-based sub-analyses
# ---------------------------------------------------------------------------

class TestRuleBasedAnalyses:

    def test_time_of_day_buckets_present(self, full_analysis):
        buckets = full_analysis["time_of_day"]["buckets"]
        assert set(buckets.keys()) == {"morning", "afternoon", "evening", "night"}

    def test_time_of_day_best_period_is_valid(self, full_analysis):
        best = full_analysis["time_of_day"]["best_period"]
        assert best in {"morning", "afternoon", "evening", "night"}

    def test_session_length_buckets_present(self, full_analysis):
        buckets = full_analysis["session_length"]["buckets"]
        assert set(buckets.keys()) == {"short", "medium", "long", "marathon"}

    def test_distractions_ranked_covers_all_types(self, full_analysis):
        ranked = full_analysis["distractions"]["ranked_by_count"]
        labels = {r["type"] for r in ranked}
        assert labels == {"Phone", "Looking Away", "Left Desk", "App Switch", "Idle"}

    def test_distraction_percentages_sum_to_100(self, full_analysis):
        ranked = full_analysis["distractions"]["ranked_by_count"]
        total_pct = sum(r["pct_of_all_events"] for r in ranked)
        assert abs(total_pct - 100.0) < 0.5  # allow minor rounding error

    def test_focus_trend_has_valid_direction(self, full_analysis):
        trend = full_analysis["trend"]["trend"]
        assert trend in {"improving", "declining", "stable", "insufficient_data"}

    def test_focus_trend_rolling_avg_length(self, full_analysis):
        rolling = full_analysis["trend"]["rolling_avg"]
        assert len(rolling) == full_analysis["session_count"]

    def test_peak_focus_peak_hour_in_range(self, full_analysis):
        peak_hour = full_analysis["peak_focus"]["peak_hour"]
        # May be None if no hour has >= 2 sessions, but mock data should have one
        if peak_hour is not None:
            assert 0 <= peak_hour <= 23


# ---------------------------------------------------------------------------
# ML: feature importance
# ---------------------------------------------------------------------------

class TestMLFeatureImportance:

    def test_returns_all_eight_features(self, full_analysis):
        features = full_analysis["ml_feature_importance"]["features"]
        assert len(features) == 8

    def test_importance_pct_sums_to_100(self, full_analysis):
        features = full_analysis["ml_feature_importance"]["features"]
        total = sum(f["importance_pct"] for f in features)
        assert abs(total - 100.0) < 0.5

    def test_features_sorted_descending(self, full_analysis):
        features = full_analysis["ml_feature_importance"]["features"]
        importances = [f["importance"] for f in features]
        assert importances == sorted(importances, reverse=True)

    def test_r2_score_in_valid_range(self, full_analysis):
        r2 = full_analysis["ml_feature_importance"]["r2_score"]
        assert r2 is not None
        assert 0.0 <= r2 <= 1.0

    def test_top_factor_is_a_string(self, full_analysis):
        top = full_analysis["ml_feature_importance"]["top_factor"]
        assert isinstance(top, str)
        assert len(top) > 0

    def test_insufficient_data_returns_error(self, analyzer_empty):
        result = analyzer_empty.ml_feature_importance([])
        assert result["error"] == "insufficient_data"
        assert result["features"] == []
        assert result["r2_score"] is None


# ---------------------------------------------------------------------------
# ML: session clustering
# ---------------------------------------------------------------------------

class TestMLClustering:

    def test_correct_number_of_clusters(self, full_analysis):
        clusters = full_analysis["ml_clusters"]["clusters"]
        assert len(clusters) == 3

    def test_all_sessions_assigned(self, full_analysis):
        clusters = full_analysis["ml_clusters"]["clusters"]
        total_assigned = sum(c["session_count"] for c in clusters)
        assert total_assigned == full_analysis["session_count"]

    def test_no_duplicate_session_ids(self, full_analysis):
        clusters = full_analysis["ml_clusters"]["clusters"]
        all_ids = [sid for c in clusters for sid in c["session_ids"]]
        assert len(all_ids) == len(set(all_ids))

    def test_clusters_sorted_by_score_descending(self, full_analysis):
        clusters = full_analysis["ml_clusters"]["clusters"]
        scores = [c["avg_score"] for c in clusters]
        assert scores == sorted(scores, reverse=True)

    def test_cluster_labels_are_valid(self, full_analysis):
        valid_labels = {"High Focus", "Moderate Focus", "Needs Improvement"}
        for c in full_analysis["ml_clusters"]["clusters"]:
            assert c["label"] in valid_labels

    def test_cluster_avg_scores_in_range(self, full_analysis):
        for c in full_analysis["ml_clusters"]["clusters"]:
            assert 0 <= c["avg_score"] <= 100

    def test_cluster_avg_hour_in_range(self, full_analysis):
        for c in full_analysis["ml_clusters"]["clusters"]:
            assert 0 <= c["avg_hour"] <= 23

    def test_insufficient_data_returns_error(self, analyzer_empty):
        result = analyzer_empty.ml_cluster_sessions([])
        assert result["error"] == "insufficient_data"
        assert result["clusters"] == []


# ---------------------------------------------------------------------------
# ML: trend forecasting
# ---------------------------------------------------------------------------

class TestMLForecast:

    def test_direction_is_valid(self, full_analysis):
        direction = full_analysis["ml_forecast"]["direction"]
        assert direction in {"improving", "declining", "stable"}

    def test_predicts_five_sessions(self, full_analysis):
        preds = full_analysis["ml_forecast"]["predicted_next_5"]
        assert len(preds) == 5

    def test_predictions_in_valid_score_range(self, full_analysis):
        for p in full_analysis["ml_forecast"]["predicted_next_5"]:
            assert 0 <= p <= 100

    def test_r2_score_in_valid_range(self, full_analysis):
        r2 = full_analysis["ml_forecast"]["r2_score"]
        assert r2 is not None
        assert -1.0 <= r2 <= 1.0  # R² can be negative for a poor fit

    def test_slope_matches_direction(self, full_analysis):
        slope = full_analysis["ml_forecast"]["slope"]
        direction = full_analysis["ml_forecast"]["direction"]
        if direction == "improving":
            assert slope > 0.5
        elif direction == "declining":
            assert slope < -0.5
        else:
            assert -0.5 <= slope <= 0.5

    def test_insufficient_data_returns_error(self, analyzer_empty):
        result = analyzer_empty.ml_forecast_trend([])
        assert result["error"] == "insufficient_data"
        assert result["predicted_next_5"] == []


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------

class TestMarkdownReport:

    def test_report_is_written(self, analyzer_mock, tmp_path):
        out = str(tmp_path / "report.md")
        returned_path = analyzer_mock.generate_markdown_report(out)
        assert returned_path is not None
        assert os.path.exists(out)

    def test_report_contains_key_sections(self, analyzer_mock, tmp_path):
        out = str(tmp_path / "report.md")
        analyzer_mock.generate_markdown_report(out)
        content = open(out, encoding="utf-8").read()
        for heading in [
            "# Study Session Pattern Analysis Report",
            "## Summary",
            "## Key Insights",
            "## Machine Learning Analysis",
            "### What Affects Your Focus Most",
            "### Your Session Profiles",
            "### Score Forecast",
            "## Detailed Breakdowns",
        ]:
            assert heading in content, f"Missing section: {heading}"

    def test_report_contains_ml_table(self, analyzer_mock, tmp_path):
        out = str(tmp_path / "report.md")
        analyzer_mock.generate_markdown_report(out)
        content = open(out, encoding="utf-8").read()
        # Feature importance table should have rank column
        assert "| Rank | Factor | Importance |" in content

    def test_empty_db_report_returns_none(self, analyzer_empty):
        result = analyzer_empty.generate_markdown_report("should_not_exist.md")
        assert result is None
        assert not os.path.exists("should_not_exist.md")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
