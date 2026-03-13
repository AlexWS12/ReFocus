from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from src.core.qApplication import QApplication
from src.experience.button import Button

from src.experience.widgets.petView import PetView
from src.experience.widgets.calender import Calender

class dashboard(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self.data = self.app.database_reader.load_dashboard_data()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Dashboard"))

        start_btn = Button("Start Session")
        start_btn.clicked.connect(self.start_session)
        self.layout.addWidget(start_btn)

        self.pet = PetView(self)
        self.layout.addWidget(self.pet)

        self.calender = Calender(self)
        self.layout.addWidget(self.calender)
    
    def start_session(self):
        self.app.main_window.hide()
        self.app.pet_window.show()
        self.app.position_pet_window()