from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt
from src.core.qApplication import QApplication

from src.experience.widgets.lifetime_focus import LifetimeFocus
from src.experience.widgets.total_sessions import TotalSessions
from src.experience.widgets.longest_focus import LongestFocus
from src.experience.widgets.total_exp import TotalExp
from src.experience.widgets.focus_trend_chart import FocusTrendChart
from src.experience.widgets.distraction_chart import DistractionChart
from src.experience.widgets.time_of_day_chart import TimeOfDayChart
from src.experience.widgets.session_length_chart import SessionLengthChart
from src.experience.widgets.peak_hours_chart import PeakHoursChart


class Report(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.app = QApplication.instance()

        self.data = self.app.database_reader.load_report_data()
        self.data['total_exp'] = parent.data['exp']

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        scroll.setWidget(container)

        stats_grid = QGridLayout()
        self.lifetime_focus = LifetimeFocus(self)
        self.total_sessions = TotalSessions(self)
        self.longest_focus = LongestFocus(self)
        self.total_exp = TotalExp(self)
        stats_grid.addWidget(self.lifetime_focus, 0, 0)
        stats_grid.addWidget(self.total_sessions, 0, 1)
        stats_grid.addWidget(self.longest_focus, 1, 0)
        stats_grid.addWidget(self.total_exp, 1, 1)
        self._layout.addLayout(stats_grid)

        self.focus_trend = FocusTrendChart(self)
        self._layout.addWidget(self.focus_trend)

        charts_grid = QGridLayout()
        self.distraction_chart = DistractionChart(self)
        self.time_of_day_chart = TimeOfDayChart(self)
        self.session_length_chart = SessionLengthChart(self)
        self.peak_hours_chart = PeakHoursChart(self)
        charts_grid.addWidget(self.distraction_chart, 0, 0)
        charts_grid.addWidget(self.time_of_day_chart, 0, 1)
        charts_grid.addWidget(self.session_length_chart, 1, 0)
        charts_grid.addWidget(self.peak_hours_chart, 1, 1)
        self._layout.addLayout(charts_grid)

    def showEvent(self, event):
        super().showEvent(event)
        self.data = self.app.database_reader.load_report_data()
        self.data['total_exp'] = self.app.database_reader.get_topbar_data().get('exp', 0)
        self.lifetime_focus.refresh(self.data)
        self.total_sessions.refresh(self.data)
        self.longest_focus.refresh(self.data)
        self.total_exp.refresh(self.data)
        self.focus_trend.refresh(self.data)
        self.distraction_chart.refresh(self.data)
        self.time_of_day_chart.refresh(self.data)
        self.session_length_chart.refresh(self.data)
        self.peak_hours_chart.refresh(self.data)
