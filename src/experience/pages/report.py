from PySide6.QtWidgets import QWidget, QGridLayout
from src.core.qApplication import QApplication

from src.experience.widgets.lifetime_focus import LifetimeFocus
from src.experience.widgets.total_sessions import TotalSessions
from src.experience.widgets.longest_focus import LongestFocus
from src.experience.widgets.total_exp import TotalExp

class Report(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        self.app = QApplication.instance()

        # load report data
        self.data = self.app.database_reader.load_report_data()

        # add total exp to the data
        self.data['total_exp'] = parent.data['exp']

        # layout for the report
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        # add widgets to the grid layout
        self.layout.addWidget(LifetimeFocus(self), 0, 0)
        self.layout.addWidget(TotalSessions(self), 0, 1)
        self.layout.addWidget(LongestFocus(self), 1, 0)
        self.layout.addWidget(TotalExp(self), 1, 1)