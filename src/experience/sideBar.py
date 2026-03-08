from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from src.experience.button import Button

from typing import TYPE_CHECKING # avoid circular imports

if TYPE_CHECKING: 
    from src.experience.mainWindow import MainWindow

class Sidebar(QWidget):
    def __init__(self, main_window : MainWindow):
        super().__init__()
        self.main_window = main_window

        # layout for sidebar
        self.layout = QVBoxLayout() 
        self.setLayout(self.layout)

        self.add_buttons()

    # add widget to sidebar
    def add_items(self, widget: QWidget):
        self.layout.addWidget(widget)

    # add all the navigation buttons to sidebar
    def add_buttons(self):

        # intialize navigation buttons
        dashboard_button = Button("Dashboard")
        dashboard_button.clicked.connect(lambda: self.main_window.pages_stack.setCurrentIndex(0))

        session_button = Button("Session")
        session_button.clicked.connect(lambda: self.main_window.pages_stack.setCurrentIndex(1))

        report_button = Button("Report")
        report_button.clicked.connect(lambda: self.main_window.pages_stack.setCurrentIndex(2))

        virtualPet_button = Button("Virtual Pet")
        virtualPet_button.clicked.connect(lambda: self.main_window.pages_stack.setCurrentIndex(3))

        achievements_button = Button("Achievement")
        achievements_button.clicked.connect(lambda: self.main_window.pages_stack.setCurrentIndex(4))

        self.add_items(dashboard_button)
        self.add_items(session_button)
        self.add_items(report_button)
        self.add_items(virtualPet_button)
        self.add_items(achievements_button)

