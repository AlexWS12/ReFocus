from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class report(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Report"))