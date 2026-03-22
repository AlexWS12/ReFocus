from PySide6.QtWidgets import QWidget, QVBoxLayout

from src.experience.widgets.centered_label import CenteredLabel


class LongestFocus(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(CenteredLabel("Longest Focus"))
        self.layout.addWidget(
            CenteredLabel(f"{parent.data['session_analytics']['longest_focus_seconds']} seconds", secondary=True)
        )