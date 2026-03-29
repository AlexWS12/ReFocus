from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout

from src.experience.widgets.centered_label import CenteredLabel


class PreviousSession(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(CenteredLabel("Previous Session"))
        self._score_label = CenteredLabel("", secondary=True)
        self._focus_label = CenteredLabel("", secondary=True)
        self._events_label = CenteredLabel("", secondary=True)
        self.layout.addWidget(self._score_label)
        self.layout.addWidget(self._focus_label)
        self.layout.addWidget(self._events_label)
        self.refresh(parent.data)

    def refresh(self, data):
        prev = data.get("previous_session_data") or {}
        score = prev.get("score") or 0
        focus_pct = prev.get("focus_percentage") or 0
        events = prev.get("events") or 0
        self._score_label.setText(f"Score: {score:.2f}")
        self._focus_label.setText(f"Focused percentage: {focus_pct:.2f}%")
        self._events_label.setText(f"Distractions: {events}")