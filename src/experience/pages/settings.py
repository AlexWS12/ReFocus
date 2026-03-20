from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from src.experience.widgets.centered_label import CenteredLabel

from src.experience.button import Button

class Settings(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(CenteredLabel("Settings"))

        self.dark_mode = Button("Chnage Theme");
        self.app = QApplication.instance()
        self.layout.addWidget(self.dark_mode)

        self.dark_mode.clicked.connect(self.darkmode)

    def darkmode(self):
        if self.app.style_path == "dark.qss":
            self.app.load_stylesheet("light.qss")
            self.app.style_path = "light.qss"
        else:
            self.app.load_stylesheet("dark.qss")
            self.app.style_path = "dark.qss"
