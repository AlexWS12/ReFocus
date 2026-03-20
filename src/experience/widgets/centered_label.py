from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class CenteredLabel(QLabel):
    def __init__(self, text: str = "", parent=None, *, secondary: bool = False):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if secondary:
            self.setObjectName("secondaryLabel")
