from PySide6.QtWidgets import QFrame, QVBoxLayout

from src.experience.widgets.centered_label import CenteredLabel


class AvgFocusTime(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(CenteredLabel("Average Focus Time"))
        self.layout.addWidget(CenteredLabel(f"{parent.data['user_info']['avg_focus_time']} minutes"))