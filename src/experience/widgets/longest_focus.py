from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class longest_focus(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Longest Focus:"))
        self.layout.addWidget(QLabel(f"{parent.data['session_analytics']['longest_focus_seconds']} seconds"))