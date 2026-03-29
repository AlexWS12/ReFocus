from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication as QtApplication

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.vision_stream import VisionStream
from src.experience.widgets.distraction_list import DistractionList
from src.experience.button import Button


class Session(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        root_layout = QVBoxLayout()
        self.setLayout(root_layout)

        root_layout.addWidget(CenteredLabel("Session"))

        content_layout = QHBoxLayout()
        root_layout.addLayout(content_layout)

        self.vision_stream = VisionStream()
        content_layout.addWidget(self.vision_stream, stretch=3)

        self.distraction_list = DistractionList()
        content_layout.addWidget(self.distraction_list, stretch=2)

        self.stop_btn = Button("Stop Session")
        self.stop_btn.setObjectName("stopSessionButton")
        self.stop_btn.clicked.connect(self._stop_session)
        self.stop_btn.hide()
        root_layout.addWidget(self.stop_btn)

    def _stop_session(self):
        app = QtApplication.instance()
        app.vision_manager.stop_session()
        app.session_manager.end_session()
        app.session_manager.reset()
        app.pet_window.hide()
        self.stop_btn.hide()
        app.main_window.pages_stack.setCurrentIndex(0)

    def showEvent(self, event):
        super().showEvent(event)
        app = QtApplication.instance()
        from src.intelligence.session_manager import SessionState
        if app.session_manager.session_state == SessionState.IN_PROGRESS:
            self.stop_btn.show()
        else:
            self.stop_btn.hide()
        self.distraction_list.start_polling()

    def hideEvent(self, event):
        self.distraction_list.stop_polling()
        super().hideEvent(event)