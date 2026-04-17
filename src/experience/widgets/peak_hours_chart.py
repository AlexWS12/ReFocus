from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet,
    QBarCategoryAxis, QValueAxis,
)

from src.experience.widgets.centered_label import CenteredLabel

_DEFAULT_COLOR = QColor("#3b7deb")
_PEAK_COLOR = QColor("#27ae60")


def _hour_label(h: int) -> str:
    am_pm = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}{am_pm}"


class PeakHoursChart(QFrame):
    # Bar chart showing average focus score per hour of day

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)

        layout.addWidget(CenteredLabel("Peak Focus Hours"))

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

        pf = pa.get("peak_focus", {})
        hourly_avg = pf.get("hourly_avg", {})
        peak_hour = pf.get("peak_hour")

        if not hourly_avg:
            self._info_label.setText("Not enough data per hour yet")
            return

        sorted_hours = sorted(hourly_avg.keys())

        categories = []
        series = QBarSeries()

        for h in sorted_hours:
            avg = hourly_avg[h]
            bar_set = QBarSet(_hour_label(h))
            bar_set.append(avg)
            bar_set.setColor(_PEAK_COLOR if h == peak_hour else _DEFAULT_COLOR)
            series.append(bar_set)
            categories.append(_hour_label(h))

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

        if peak_hour is not None:
            self._info_label.setText(f"Sharpest at {_hour_label(peak_hour)}")
        else:
            self._info_label.setText("")
