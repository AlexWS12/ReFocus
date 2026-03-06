from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class virtualPet(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        layout.addWidget(QLabel("Virtual Pet"))