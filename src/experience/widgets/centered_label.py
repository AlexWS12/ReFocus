from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class CenteredLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
