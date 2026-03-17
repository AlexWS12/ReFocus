from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout
from src.core.qApplication import QApplication
from src.experience.button import Button

from src.experience.widgets.pet_view import PetView
from src.experience.widgets.calendar import Calendar
from src.experience.widgets.avg_focus_time import AvgFocusTime
from src.experience.widgets.previous_session import PreviousSession

class Dashboard(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        self.app = QApplication.instance()

        # load dashboard data
        self.data = self.app.database_reader.load_dashboard_data()

        # layout for the dashboard
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # grid layout for the dashboard
        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        # add widgets to the grid layout
        self.AvgFocusTime = AvgFocusTime(self)
        self.grid_layout.addWidget(self.AvgFocusTime, 0, 0)

        self.PetView = PetView(self)
        self.grid_layout.addWidget(self.PetView, 0, 1)

        self.Calendar = Calendar(self)
        self.grid_layout.addWidget(self.Calendar, 1, 0)

        self.PreviousSession = PreviousSession(self)
        self.grid_layout.addWidget(self.PreviousSession, 1, 1)

        # add start session button to the layout
        start_btn = Button("Start Session")
        start_btn.clicked.connect(self.start_session)
        self.layout.addWidget(start_btn)
    
    # start session and show the pet window
    def start_session(self):
        self.app.main_window.hide()
        self.app.pet_window.show()
        self.app.position_pet_window()