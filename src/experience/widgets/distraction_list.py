from datetime import datetime

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget
from PySide6.QtWidgets import QApplication as QtApplication
from PySide6.QtCore import Qt, QTimer


DISTRACTION_LABELS = {
    "phone_distraction": "Phone Detected",
    "look_away_distraction": "Looked Away",
    "left_desk_distraction": "Left Desk",
    "app_distraction": "App Distraction",
    "idle_distraction": "Idle",
}

_MERGE_WINDOW_SECONDS = 30
_ROW_STYLE = (
    "background-color: #fff3f3; border: 1px solid #f5c6cb; "
    "border-radius: 6px; padding: 6px 10px;"
)


class DistractionList(QFrame):
    """Scrollable list that live-updates with distractions logged during the active session.

    Consecutive events of the same type within a short time window are merged
    into a single row whose duration accumulates, so the list stays readable
    instead of filling with repeated entries.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.app = QtApplication.instance()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Recent Distractions")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignTop)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        scroll.setWidget(self._list_container)

        self._placeholder = QLabel("No distractions yet")
        self._placeholder.setObjectName("secondaryLabel")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._list_layout.addWidget(self._placeholder)

        self._displayed_count = 0
        self._last_row_type = None
        self._last_row_timestamp = None
        self._last_row_duration = 0
        self._last_row_label: QLabel | None = None

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(1000)

    def _poll(self):
        events = self.app.session_manager.distraction_events
        if len(events) <= self._displayed_count:
            return

        if self._displayed_count == 0:
            self._placeholder.hide()

        for event in events[self._displayed_count:]:
            dtype = event["type"].value
            duration = event["time"]
            timestamp = event["timestamp"]

            if self._should_merge(dtype, timestamp):
                self._last_row_duration += duration
                self._last_row_timestamp = timestamp
                self._update_row_text()
            else:
                self._add_row(dtype, duration, timestamp)

        self._displayed_count = len(events)

    def _should_merge(self, dtype: str, timestamp: str) -> bool:
        if self._last_row_label is None or self._last_row_type != dtype:
            return False
        try:
            prev = datetime.fromisoformat(self._last_row_timestamp)
            curr = datetime.fromisoformat(timestamp)
            return (curr - prev).total_seconds() <= _MERGE_WINDOW_SECONDS
        except (ValueError, TypeError):
            return False

    def _add_row(self, dtype: str, duration: int, timestamp: str):
        label_text = DISTRACTION_LABELS.get(dtype, dtype)
        ts_short = timestamp.split("T")[-1]

        row = QLabel(f"{ts_short}  —  {label_text}  ({duration}s)")
        row.setObjectName("secondaryLabel")
        row.setStyleSheet(_ROW_STYLE)
        self._list_layout.addWidget(row)

        self._last_row_type = dtype
        self._last_row_timestamp = timestamp
        self._last_row_duration = duration
        self._last_row_label = row

    def _update_row_text(self):
        label_text = DISTRACTION_LABELS.get(self._last_row_type, self._last_row_type)
        ts_short = self._last_row_timestamp.split("T")[-1]
        self._last_row_label.setText(
            f"{ts_short}  —  {label_text}  ({self._last_row_duration}s)"
        )

    def reset(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._placeholder = QLabel("No distractions yet")
        self._placeholder.setObjectName("secondaryLabel")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._list_layout.addWidget(self._placeholder)

        self._displayed_count = 0
        self._last_row_type = None
        self._last_row_timestamp = None
        self._last_row_duration = 0
        self._last_row_label = None

    def start_polling(self):
        self.reset()
        self._poll_timer.start(1000)

    def stop_polling(self):
        self._poll_timer.stop()
