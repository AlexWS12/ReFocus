from PySide6.QtWidgets import QWidget, QVBoxLayout

from src.experience.widgets.centered_label import CenteredLabel


class TotalSessions(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(CenteredLabel("Total Sessions"))
        self.layout.addWidget(CenteredLabel(f"{parent.data['session_analytics']['total_sessions']}"))