from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel,
    QApplication as QtApplication,
)
from PySide6.QtCore import Qt

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.vision_stream import VisionStream
from src.experience.widgets.distraction_list import DistractionList
from src.experience.widgets.session_report import SessionReport
from src.experience.button import Button

_CTA_VIEW = 0
_LIVE_VIEW = 1
_REPORT_VIEW = 2


class Session(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack)

        # --- CTA / idle view (index 0) ---
        cta_page = QWidget()
        cta_layout = QVBoxLayout(cta_page)
        cta_layout.setAlignment(Qt.AlignCenter)

        cta_title = QLabel("Ready to focus?")
        cta_title.setAlignment(Qt.AlignCenter)
        cta_title.setStyleSheet("font-size: 28px; font-weight: bold;")
        cta_layout.addWidget(cta_title)

        cta_subtitle = QLabel("Start a session to track your attention and log distractions.")
        cta_subtitle.setAlignment(Qt.AlignCenter)
        cta_subtitle.setObjectName("secondaryLabel")
        cta_subtitle.setStyleSheet("font-size: 14px; margin-top: 4px;")
        cta_layout.addWidget(cta_subtitle)

        cta_layout.addSpacing(24)

        start_btn = Button("Start Session")
        start_btn.setObjectName("startSessionButton")
        start_btn.setFixedWidth(220)
        start_btn.clicked.connect(self._go_to_setup)
        cta_layout.addWidget(start_btn, alignment=Qt.AlignCenter)

        self._stack.addWidget(cta_page)

        # --- Live session view (index 1) ---
        live_page = QWidget()
        live_layout = QVBoxLayout(live_page)

        live_layout.addWidget(CenteredLabel("Session"))

        content_layout = QHBoxLayout()
        live_layout.addLayout(content_layout)

        self.vision_stream = VisionStream()
        content_layout.addWidget(self.vision_stream, stretch=1)

        self.distraction_list = DistractionList()
        content_layout.addWidget(self.distraction_list, stretch=1)

        self.stop_btn = Button("Stop Session")
        self.stop_btn.setObjectName("stopSessionButton")
        self.stop_btn.clicked.connect(self._stop_session)
        live_layout.addWidget(self.stop_btn)

        self._stack.addWidget(live_page)

        # --- Report view (index 2) ---
        report_page = QWidget()
        report_layout = QVBoxLayout(report_page)

        self.session_report = SessionReport()
        report_layout.addWidget(self.session_report)

        self.back_btn = Button("Back to Dashboard")
        self.back_btn.setObjectName("startSessionButton")
        self.back_btn.clicked.connect(self._back_to_dashboard)
        report_layout.addWidget(self.back_btn)

        self._stack.addWidget(report_page)

    def _go_to_setup(self):
        app = QtApplication.instance()
        app.main_window.pages_stack.setCurrentIndex(6)

    def _stop_session(self):
        app = QtApplication.instance()
        app.vision_manager.stop_session()
        app.session_manager.end_session()
        app.pet_window.hide()
        self.distraction_list.stop_polling()

        report_data = app.session_manager.session_report()
        app.session_manager.reset()

        from src.intelligence.session_feedback import generate_brief_feedback
        feedback = generate_brief_feedback(report_data, app.database_reader.get_cached_analysis())
        self.session_report.load(report_data, feedback=feedback)
        self._stack.setCurrentIndex(_REPORT_VIEW)
        app.main_window.show()
        app.main_window.raise_()

    def _back_to_dashboard(self):
        app = QtApplication.instance()
        self._stack.setCurrentIndex(_CTA_VIEW)
        app.main_window.pages_stack.setCurrentIndex(0)

    def showEvent(self, event):
        super().showEvent(event)
        app = QtApplication.instance()
        from src.intelligence.session_manager import SessionState
        if app.session_manager.session_state == SessionState.IN_PROGRESS:
            self._stack.setCurrentIndex(_LIVE_VIEW)
            self.distraction_list.start_polling()
        elif self._stack.currentIndex() != _REPORT_VIEW:
            self._stack.setCurrentIndex(_CTA_VIEW)

    def hideEvent(self, event):
        self.distraction_list.stop_polling()
        super().hideEvent(event)