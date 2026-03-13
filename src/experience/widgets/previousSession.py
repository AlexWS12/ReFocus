from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class previousSession(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # self.layout.addWidget(QLabel(f"Score:{parent.data['previous_session_data']['score'] or 0}"))
        # self.layout.addWidget(QLabel(f"Focused percentage: {parent.data['previous_session_data']['focus_percentage'] or 0}"))
        # self.layout.addWidget(QLabel(f"Number of Sessions:{parent.data['previous_session_data']['events'] or 0}"))