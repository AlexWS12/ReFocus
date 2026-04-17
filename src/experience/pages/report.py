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
from src.experience.widgets.report_pet_widget import ReportPetWidget
from src.experience.widgets.forecast_chart import ForecastChart
from src.experience.widgets.feature_importance_widget import FeatureImportanceWidget
from src.experience.widgets.ai_insight_widget import AiInsightWidget


class Report(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.app = QApplication.instance()

        self.data = self.app.database_reader.load_report_data()
        self.data['total_exp'] = parent.data['exp']

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        container.setObjectName("reportContainer")
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

        charts_section = QWidget()
        charts_section.setObjectName("reportChartsContainer")
        charts_grid = QGridLayout(charts_section)
        self.distraction_chart = DistractionChart(self)
        self.time_of_day_chart = TimeOfDayChart(self)
        self.session_length_chart = SessionLengthChart(self)
        self.peak_hours_chart = PeakHoursChart(self)
        charts_grid.addWidget(self.distraction_chart, 0, 0)
        charts_grid.addWidget(self.time_of_day_chart, 0, 1)
        charts_grid.addWidget(self.session_length_chart, 1, 0)
        charts_grid.addWidget(self.peak_hours_chart, 1, 1)
        self._layout.addWidget(charts_section)

        ml_section = QWidget()
        ml_section.setObjectName("reportChartsContainer")
        ml_grid = QGridLayout(ml_section)
        self.forecast_chart = ForecastChart(self)
        self.feature_importance = FeatureImportanceWidget(self)
        ml_grid.addWidget(self.forecast_chart, 0, 0)
        ml_grid.addWidget(self.feature_importance, 0, 1)
        self._layout.addWidget(ml_section)

        self.ai_insight = AiInsightWidget(self)
        self._layout.addWidget(self.ai_insight)

        # Floating pet-insight panel pinned to the report page corner.
        self.pet_widget = ReportPetWidget(self)
        self.pet_widget.layout_changed.connect(self._position_pet_widget)
        self.pet_widget.raise_()
        self.pet_widget.refresh(self.data)
        self._position_pet_widget()

    def showEvent(self, event):
        super().showEvent(event)
        self.pet_widget.show()
        # refresh fast data immediately from cache (no ML blocking)
        self.data = self.app.database_reader.load_report_data()
        self.data['total_exp'] = (self.app.database_reader.get_topbar_data() or {}).get('exp', 0)
        self._refresh_all_widgets()
        # kick off a fresh background analysis; _on_analysis_ready updates charts when done
        self.app.database_reader.run_analysis_async(callback=self._on_analysis_ready)

    def _on_analysis_ready(self, result):
        try:
            self.data['pattern_analysis'] = result
            self._refresh_all_widgets()
        except RuntimeError:
            pass  # widget was deleted before analysis finished

    def _refresh_all_widgets(self):
        self.lifetime_focus.refresh(self.data)
        self.total_sessions.refresh(self.data)
        self.longest_focus.refresh(self.data)
        self.total_exp.refresh(self.data)
        self.focus_trend.refresh(self.data)
        self.distraction_chart.refresh(self.data)
        self.time_of_day_chart.refresh(self.data)
        self.session_length_chart.refresh(self.data)
        self.peak_hours_chart.refresh(self.data)
        self.forecast_chart.refresh(self.data)
        self.feature_importance.refresh(self.data)
        self.ai_insight.refresh(self.data)
        self.pet_widget.refresh(self.data)
        self._position_pet_widget()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_pet_widget()

    def _position_pet_widget(self):
        margin = 16
        self.pet_widget.adjustSize()
        x = self.width() - self.pet_widget.width() - margin
        y = self.height() - self.pet_widget.height() - margin
        self.pet_widget.move(max(0, x), max(0, y))
        self.pet_widget.raise_()
