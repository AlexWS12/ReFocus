from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout

from src.experience.widgets.centered_label import CenteredLabel


class LongestFocus(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(CenteredLabel("Longest Focus"))
        self._value_label = CenteredLabel("", secondary=True)
        self.layout.addWidget(self._value_label)
        self.refresh(parent.data)

    def refresh(self, data):
        seconds = data.get("session_analytics", {}).get("longest_focus_seconds", 0)
        self._value_label.setText(f"{seconds} seconds")