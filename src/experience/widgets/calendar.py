from PySide6.QtWidgets import QCalendarWidget


class Calendar(QCalendarWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.setMaximumWidth(280)
        self.setMaximumHeight(220)
