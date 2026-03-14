from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class PreviousSession(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.prev = parent.data.get("previous_session_data") or {}

        self.layout.addWidget(QLabel(f"Score:{self.prev.get("score") or 0}"))
        self.layout.addWidget(QLabel(f"Focused percentage: {self.prev.get("focus_percentage") or 0}"))
        self.layout.addWidget(QLabel(f"Number of Sessions:{self.prev.get("events") or 0}"))