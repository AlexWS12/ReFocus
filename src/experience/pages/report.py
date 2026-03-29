from PySide6.QtWidgets import QWidget, QGridLayout
from src.core.qApplication import QApplication

from src.experience.widgets.lifetime_focus import LifetimeFocus
from src.experience.widgets.total_sessions import TotalSessions
from src.experience.widgets.longest_focus import LongestFocus
from src.experience.widgets.total_exp import TotalExp

class Report(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.app = QApplication.instance()

        # load report data
        self.data = self.app.database_reader.load_report_data()
        self.data['total_exp'] = parent.data['exp']

        # layout for the report
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        # add widgets to the grid layout
        self.lifetime_focus = LifetimeFocus(self)
        self.total_sessions = TotalSessions(self)
        self.longest_focus = LongestFocus(self)
        self.total_exp = TotalExp(self)
        self.layout.addWidget(self.lifetime_focus, 0, 0)
        self.layout.addWidget(self.total_sessions, 0, 1)
        self.layout.addWidget(self.longest_focus, 1, 0)
        self.layout.addWidget(self.total_exp, 1, 1)

    def showEvent(self, event):
        super().showEvent(event)
        self.data = self.app.database_reader.load_report_data()
        self.data['total_exp'] = self.app.database_reader.get_topbar_data().get('exp', 0)
        self.lifetime_focus.refresh(self.data)
        self.total_sessions.refresh(self.data)
        self.longest_focus.refresh(self.data)
        self.total_exp.refresh(self.data)