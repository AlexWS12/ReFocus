from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.button import Button
from src.core.qApplication import QApplication

class Setup(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)

        self.app = QApplication.instance()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(CenteredLabel("Setup"))

        # add start session button to the layout
        start_btn = Button("Start Session")
        start_btn.setObjectName("startSessionButton")
        start_btn.clicked.connect(self.start_session)
        self.layout.addWidget(start_btn)

    # start session and show the pet window
    def start_session(self):
        self.app.main_window.pages_stack.setCurrentIndex(1)
        self.app.main_window.hide()
        self.app.pet_window.show()
        self.app.position_pet_window()
