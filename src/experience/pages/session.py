from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class Session(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        # layout for the session
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Session"))