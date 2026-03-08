from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from src.core.qApplication import QApplication
from src.experience.button import Button

class dashboard(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Dashboard"))

        start_btn = Button("Start Session")
        start_btn.clicked.connect(self.start_session)
        self.layout.addWidget(start_btn)
    
    def start_session(self):
        app = QApplication.instance()
        app.main_window.hide()
        app.pet_window.show()
        app.position_pet_window()