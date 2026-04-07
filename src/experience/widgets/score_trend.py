from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QPen, QColor, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QAreaSeries

from src.experience.widgets.centered_label import CenteredLabel

_ACCENT = QColor("#3b7deb")
_ACCENT_FILL = QColor(59, 125, 235, 40)


class ScoreTrend(QFrame):
    """Dashboard card showing a sparkline of recent session scores."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)

        layout.addWidget(CenteredLabel("Score Trend"))

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setMargins(QMargins(4, 4, 4, 4))

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent; border: none;")
        self._chart_view.setMinimumHeight(120)
        layout.addWidget(self._chart_view)

        self._avg_label = CenteredLabel("", secondary=True)
        layout.addWidget(self._avg_label)

        self.refresh(parent.data)

    def refresh(self, data):
        scores = data.get("recent_scores", [])

        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)

        if not scores:
            self._avg_label.setText("No sessions yet")
            return

        upper = QLineSeries()
        for i, score in enumerate(scores):
            upper.append(i, score)

        pen = QPen(_ACCENT, 2)
        upper.setPen(pen)

        area = QAreaSeries(upper)
        area.setPen(pen)
        area.setBrush(_ACCENT_FILL)

        self._chart.addSeries(area)
        self._chart.addSeries(upper)

        axis_x = QValueAxis()
        axis_x.setRange(0, max(len(scores) - 1, 1))
        axis_x.setVisible(False)

        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setVisible(False)

        self._chart.addAxis(axis_x, Qt.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignLeft)

        for series in self._chart.series():
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)

        avg = sum(scores) / len(scores)
        self._avg_label.setText(f"Avg: {avg:.0f} / 100  ({len(scores)} sessions)")
