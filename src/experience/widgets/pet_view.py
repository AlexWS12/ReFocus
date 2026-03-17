from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from src.experience.widgets.centered_label import CenteredLabel


class PetView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.image = QPixmap("src/experience/static/Panther.png")

        self.label = CenteredLabel("")
        scaled = self.image.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

        self.layout.addWidget(self.label)




        
