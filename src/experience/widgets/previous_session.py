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

        self.prev = parent.data.get("previous_session_data") or {}

        self.layout.addWidget(CenteredLabel("Previous Session"))
        self.layout.addWidget(CenteredLabel(f"Score:{self.prev.get('score') or 0}", secondary=True))
        self.layout.addWidget(
            CenteredLabel(f"Focused percentage: {self.prev.get('focus_percentage') or 0}", secondary=True)
        )
        self.layout.addWidget(
            CenteredLabel(f"Number of Sessions:{self.prev.get('events') or 0}", secondary=True)
        )