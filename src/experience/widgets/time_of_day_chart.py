from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet,
    QBarCategoryAxis, QValueAxis,
)

from src.experience.widgets.centered_label import CenteredLabel

_DEFAULT_COLOR = QColor("#3b7deb")
_BEST_COLOR = QColor("#27ae60")
_PERIODS = ["morning", "afternoon", "evening", "night"]
_LABELS = {"morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "night": "Night"}


class TimeOfDayChart(QFrame):
    """Bar chart comparing average focus score across time-of-day buckets."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)

        layout.addWidget(CenteredLabel("Best Time to Study"))

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
            self._info_label.setText("Need 10+ sessions for analysis")
            return

        tod = pa.get("time_of_day", {})
        buckets = tod.get("buckets", {})
        best_period = tod.get("best_period")

        categories = []
        series = QBarSeries()

        for period in _PERIODS:
            info = buckets.get(period, {})
            avg = info.get("avg_score") or 0
            count = info.get("count", 0)

            bar_set = QBarSet(_LABELS[period])
            bar_set.append(avg)
            bar_set.setColor(_BEST_COLOR if period == best_period else _DEFAULT_COLOR)
            series.append(bar_set)
            categories.append(f"{_LABELS[period]}\n({count})")

        self._chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        self._chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setLabelFormat("%d")
        axis_y.setGridLineColor(QColor(200, 200, 200, 60))
        self._chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        if best_period:
            self._info_label.setText(f"You focus best in the {best_period}")
        else:
            self._info_label.setText("")
