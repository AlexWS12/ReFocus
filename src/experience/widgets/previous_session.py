from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import QChart, QChartView, QPieSeries

from src.experience.widgets.centered_label import CenteredLabel

_FOCUS_COLOR = QColor("#27ae60")
_DISTRACT_COLOR = QColor("#e74c3c")


class PreviousSession(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)

        layout.addWidget(CenteredLabel("Previous Session"))

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setMargins(QMargins(0, 0, 0, 0))

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent; border: none;")
        self._chart_view.setMinimumHeight(130)
        layout.addWidget(self._chart_view)

        self._detail_label = CenteredLabel("", secondary=True)
        layout.addWidget(self._detail_label)

        self.refresh(parent.data)

    def refresh(self, data):
        prev = data.get("previous_session_data") or {}

        self._chart.removeAllSeries()

        focused = prev.get("focused_time") or 0
        distracted = prev.get("distraction_time") or 0
        score = prev.get("score") or 0

        if focused == 0 and distracted == 0:
            self._detail_label.setText("No sessions yet")
            return

        series = QPieSeries()
        series.setHoleSize(0.55)

        focused_slice = series.append("Focused", focused)
        focused_slice.setColor(_FOCUS_COLOR)
        focused_slice.setBorderWidth(0)

        distract_slice = series.append("Distracted", distracted)
        distract_slice.setColor(_DISTRACT_COLOR)
        distract_slice.setBorderWidth(0)

        self._chart.addSeries(series)

        events = prev.get("events") or 0
        self._detail_label.setText(f"Score {score:.0f}  |  {events} distractions")
