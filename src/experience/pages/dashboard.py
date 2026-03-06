from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class dashboard(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        layout.addWidget(QLabel("Dashboard"))