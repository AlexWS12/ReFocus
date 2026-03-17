from PySide6.QtWidgets import QWidget, QVBoxLayout

from src.experience.widgets.centered_label import CenteredLabel


class VirtualPet(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        # layout for the virtual pet
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(CenteredLabel("Virtual Pet"))