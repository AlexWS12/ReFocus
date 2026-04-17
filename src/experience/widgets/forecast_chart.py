from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QPen, QColor, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QScatterSeries, QValueAxis,
)

from src.experience.widgets.centered_label import CenteredLabel

_ROLLING_COLOR  = QColor("#3b7deb")
_RAW_COLOR      = QColor(136, 146, 164, 140)
_FORECAST_COLOR = QColor("#9b59b6")

_DIRECTION_COLORS = {
    "improving": "#27ae60",
    "declining": "#e74c3c",
    "stable":    "#f5a623",
}


def _confidence_text(r2_score: float | None) -> str:
    if r2_score is None:
        return ""
    if r2_score >= 0.6:
        return "Confidence: strong pattern."
    if r2_score >= 0.3:
        return "Confidence: moderate pattern."
    return "Confidence: low pattern (results may vary)."


class ForecastChart(QFrame):

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.addWidget(CenteredLabel("Score Forecast"))

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setMargins(QMargins(4, 4, 4, 4))

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent; border: none;")
        self._chart_view.setMinimumHeight(180)
        layout.addWidget(self._chart_view)

        self._label = CenteredLabel("", secondary=True)
        layout.addWidget(self._label)

        self.refresh(parent.data)

    def refresh(self, data):
        pa = data.get("pattern_analysis")

        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)

        if pa is None:
            self._label.setStyleSheet("font-size: 15px;")
            total = (data.get("session_analytics") or {}).get("total_sessions", 0) or 0
            if total < 10:
                self._label.setText(f"Need {10 - total} more sessions for forecast")
            else:
                self._label.setText("Analysing...")
            return
        self._label.setStyleSheet("")

        forecast   = pa.get("ml_forecast", {})
        trend_data = pa.get("trend", {})
        scores     = trend_data.get("scores", [])
        preds      = forecast.get("predicted_next_5", [])

        if not scores or forecast.get("error"):
            self._label.setText("Not enough data")
            return

        n = len(scores)

        # historical raw scores as faded dots
        raw_series = QScatterSeries()
        raw_series.setMarkerSize(6)
        raw_series.setColor(_RAW_COLOR)
        raw_series.setBorderColor(QColor(0, 0, 0, 0))
        for i, s in enumerate(scores):
            raw_series.append(i, s)

        # rolling average as solid blue line
        rolling = trend_data.get("rolling_avg", [])
        rolling_line = QLineSeries()
        rolling_line.setPen(QPen(_ROLLING_COLOR, 2))
        for i, v in enumerate(rolling):
            rolling_line.append(i, v)

        # projected scores as dashed purple line — starts at last historical point
        forecast_line = QLineSeries()
        pen = QPen(_FORECAST_COLOR, 2, Qt.PenStyle.DashLine)
        forecast_line.setPen(pen)
        if rolling:
            forecast_line.append(n - 1, rolling[-1])  # connect to rolling avg end
        for j, p in enumerate(preds):
            forecast_line.append(n + j, p)

        # projected dots
        forecast_dots = QScatterSeries()
        forecast_dots.setMarkerSize(7)
        forecast_dots.setColor(_FORECAST_COLOR)
        forecast_dots.setBorderColor(QColor(0, 0, 0, 0))
        for j, p in enumerate(preds):
            forecast_dots.append(n + j, p)

        self._chart.addSeries(raw_series)
        self._chart.addSeries(rolling_line)
        self._chart.addSeries(forecast_line)
        self._chart.addSeries(forecast_dots)

        total = n + len(preds)
        axis_x = QValueAxis()
        axis_x.setRange(0, max(total - 1, 1))
        axis_x.setLabelFormat("%d")
        axis_x.setTitleText("Session")
        axis_x.setGridLineVisible(False)

        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setLabelFormat("%d")
        axis_y.setGridLineVisible(True)
        axis_y.setGridLineColor(QColor(200, 200, 200, 60))

        self._chart.addAxis(axis_x, Qt.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignLeft)

        for s in self._chart.series():
            s.attachAxis(axis_x)
            s.attachAxis(axis_y)

        direction = forecast.get("direction", "stable")
        slope     = forecast.get("slope", 0)
        color     = _DIRECTION_COLORS.get(direction, "#f5a623")
        self._label.setStyleSheet(f"color: {color};")
        if preds:
            confidence = _confidence_text(forecast.get("r2_score"))
            self._label.setText(
                f"Likely {direction} over the next 5 sessions. "
                f"Estimated score near {preds[-1]:.0f}. {confidence}".strip()
            )
        else:
            trend_hint = "up" if slope > 0 else "down" if slope < 0 else "flat"
            self._label.setText(f"Current direction looks {trend_hint}.")
