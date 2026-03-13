from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

class PetView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.image = QPixmap("src/experience/static/Panther.png")

        self.label = QLabel()
        scaled = self.image.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

        self.layout.addWidget(self.label)




        
