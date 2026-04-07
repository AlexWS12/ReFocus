from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QPen, QColor, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QValueAxis, QAreaSeries, QScatterSeries,
)

from src.experience.widgets.centered_label import CenteredLabel

_ROLLING_COLOR = QColor("#3b7deb")
_ROLLING_FILL = QColor(59, 125, 235, 30)
_RAW_COLOR = QColor(136, 146, 164, 160)

_TREND_COLORS = {
    "improving": "#27ae60",
    "declining": "#e74c3c",
    "stable": "#f5a623",
}


class FocusTrendChart(QFrame):
    """Line chart showing raw scores and a rolling-average overlay."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)

        layout.addWidget(CenteredLabel("Focus Trend"))

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setMargins(QMargins(4, 4, 4, 4))

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent; border: none;")
        self._chart_view.setMinimumHeight(180)
        layout.addWidget(self._chart_view)

        self._trend_label = CenteredLabel("", secondary=True)
        layout.addWidget(self._trend_label)

        self.refresh(parent.data)

    def refresh(self, data):
        pa = data.get("pattern_analysis")

        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)

        if pa is None:
            self._trend_label.setText("Need 10+ sessions for trend analysis")
            return

        trend_data = pa.get("trend", {})
        rolling = trend_data.get("rolling_avg", [])
        trend = trend_data.get("trend", "stable")
        delta = trend_data.get("delta", 0)
        overall = trend_data.get("overall_avg", 0)

        if not rolling:
            self._trend_label.setText("No data")
            return

        n = len(rolling)

        raw_scores = trend_data.get("scores", [])

        raw_series = QScatterSeries()
        raw_series.setMarkerSize(6)
        raw_series.setColor(_RAW_COLOR)
        raw_series.setBorderColor(QColor(0, 0, 0, 0))
        for i, score in enumerate(raw_scores):
            raw_series.append(i, score)

        rolling_line = QLineSeries()
        trend_color = QColor(_TREND_COLORS.get(trend, "#3b7deb"))

        for i, val in enumerate(rolling):
            rolling_line.append(i, val)

        pen = QPen(trend_color, 2)
        rolling_line.setPen(pen)

        area = QAreaSeries(rolling_line)
        area.setPen(QPen(trend_color, 0))
        fill = QColor(trend_color)
        fill.setAlpha(30)
        area.setBrush(fill)

        self._chart.addSeries(area)
        self._chart.addSeries(rolling_line)
        self._chart.addSeries(raw_series)

        axis_x = QValueAxis()
        axis_x.setRange(0, max(n - 1, 1))
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

        sign = "+" if delta >= 0 else ""
        self._trend_label.setText(
            f"{trend.capitalize()}  ({sign}{delta:.0f} vs avg {overall:.0f})"
        )

