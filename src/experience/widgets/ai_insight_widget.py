from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from src.experience.widgets.centered_label import CenteredLabel
from src.intelligence.session_feedback import generate_coach_paragraph


class AiInsightWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.addWidget(CenteredLabel("Coach Summary"))

        self._text = QLabel("Waiting for session data...")
        self._text.setWordWrap(True)
        self._text.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._text.setStyleSheet("font-size: 13px; padding: 4px; line-height: 1.5;")
        self._text.setMinimumHeight(80)
        layout.addWidget(self._text)

        self._last_session_count: int | None = None

    def refresh(self, data: dict):
        pa = data.get("pattern_analysis")
        if pa is None:
            self._last_session_count = None  # reset so next real refresh isn't skipped
            total = (data.get("session_analytics") or {}).get("total_sessions", 0) or 0
            if total < 10:
                self._text.setText(f"Need {10 - total} more sessions for a coach summary.")
            else:
                self._text.setText("Analysing your sessions...")
            return

        # only regenerate when new sessions have arrived
        session_count = pa.get("session_count")
        if session_count == self._last_session_count:
            return

        self._last_session_count = session_count
        self._text.setText(generate_coach_paragraph(pa))
