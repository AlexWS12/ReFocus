from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import (
    QChart, QChartView, QHorizontalBarSeries, QBarSet,
    QBarCategoryAxis, QValueAxis,
)

from src.experience.widgets.centered_label import CenteredLabel

_COLORS = [
    QColor("#e74c3c"),
    QColor("#f5a623"),
    QColor("#3b7deb"),
    QColor("#9b59b6"),
    QColor("#8892a4"),
]


class DistractionChart(QFrame):
    # Horizontal bar chart of distraction types ranked by frequency

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)

        layout.addWidget(CenteredLabel("Distraction Breakdown"))

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setMargins(QMargins(4, 4, 4, 4))

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent; border: none;")
        self._chart_view.setMinimumHeight(180)
        layout.addWidget(self._chart_view)

        self._info_label = CenteredLabel("", secondary=True)
        layout.addWidget(self._info_label)

        self.refresh(parent.data)

    def refresh(self, data):
        pa = data.get("pattern_analysis")

        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)

        if pa is None:
            self._info_label.setStyleSheet("font-size: 15px;")
            total = (data.get("session_analytics") or {}).get("total_sessions", 0) or 0
            self._info_label.setText("Analysing..." if total >= 10 else f"Need {10 - total} more sessions for analysis")
            return
        self._info_label.setStyleSheet("")

        ranked = pa.get("distractions", {}).get("ranked_by_count", [])
        ranked = [r for r in ranked if r["total_events"] > 0]

        if not ranked:
            self._info_label.setText("No distractions recorded")
            return

        categories = []
        series = QHorizontalBarSeries()

        for i, entry in enumerate(ranked):
            bar_set = QBarSet(entry["type"])
            bar_set.append(entry["total_events"])
            bar_set.setColor(_COLORS[i % len(_COLORS)])
            series.append(bar_set)
            categories.append(entry["type"])

        self._chart.addSeries(series)

        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        self._chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        max_val = max(e["total_events"] for e in ranked)
        axis_x = QValueAxis()
        axis_x.setRange(0, max_val * 1.15)
        axis_x.setLabelFormat("%d")
        axis_x.setGridLineColor(QColor(200, 200, 200, 60))
        self._chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        most = pa.get("distractions", {}).get("most_frequent", "")
        self._info_label.setText(f"Most frequent: {most}")
