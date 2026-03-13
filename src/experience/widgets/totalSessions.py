from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class totalSessions(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel(f"Total Sessions:{parent.data['session_analytics']['total_sessions']}"))