from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class avgFocusTime(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(QLabel("Average Focus Time:"))

        self.layout.addWidget(QLabel(f"{parent.data['user_info']['avg_focus_time']} minutes"))