from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class VirtualPet(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        # layout for the virtual pet
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Virtual Pet"))