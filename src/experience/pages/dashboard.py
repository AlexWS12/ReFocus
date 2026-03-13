from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout
from src.core.qApplication import QApplication
from src.experience.button import Button

from src.experience.widgets.petView import PetView
from src.experience.widgets.calender import Calender
from src.experience.widgets.avgFocusTime import avgFocusTime
from src.experience.widgets.previousSession import previousSession

class dashboard(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self.data = self.app.database_reader.load_dashboard_data()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Dashboard"))

        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.avg_focus_time = avgFocusTime(self)
        self.grid_layout.addWidget(self.avg_focus_time, 0, 0)

        self.pet = PetView(self)
        self.grid_layout.addWidget(self.pet, 0, 1)

        self.calender = Calender(self)
        self.grid_layout.addWidget(self.calender, 1, 0)

        self.previous_session = previousSession(self)
        self.grid_layout.addWidget(self.previous_session, 1, 1)

        start_btn = Button("Start Session")
        start_btn.clicked.connect(self.start_session)
        self.layout.addWidget(start_btn)
    
    def start_session(self):
        self.app.main_window.hide()
        self.app.pet_window.show()
        self.app.position_pet_window()