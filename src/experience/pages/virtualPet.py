from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from src.experience.petWindow import petWindow


class virtualPet(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Virtual Pet"))

        #  Temp: Opens the petWindow Window
        self.pet_window = petWindow()
        self.pet_window.show()