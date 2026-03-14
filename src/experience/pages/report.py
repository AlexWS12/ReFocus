from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout
from src.core.qApplication import QApplication
from src.experience.widgets.lifetime_focus import lifetime_focus
from src.experience.widgets.totalSessions import totalSessions
from src.experience.widgets.longest_focus import longest_focus
from src.experience.widgets.total_exp import total_exp

class report(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self.data = self.app.database_reader.load_report_data()
        self.data['total_exp'] = parent.data['exp']

        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(lifetime_focus(self), 0, 0)
        self.layout.addWidget(totalSessions(self), 0, 1)
        self.layout.addWidget(longest_focus(self), 1, 0)
        self.layout.addWidget(total_exp(self), 1, 1)