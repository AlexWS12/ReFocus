from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.pet_view import PetView


class VirtualPet(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)

        self.layout.addWidget(CenteredLabel("Virtual Pet"))
        self.layout.addWidget(PetView(self))