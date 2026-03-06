from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel

from typing import TYPE_CHECKING # avoid circular imports

if TYPE_CHECKING: 
    from src.experience.mainWindow import MainWindow

class Sidebar(QWidget):
    def __init__(self, main_window : MainWindow):
        super().__init__()
        self.main_window = main_window
        self.layout = QVBoxLayout() 
        self.setLayout(self.layout)

        self.add_items(QLabel("Sidebar"))

    def add_items(self, widget: QWidget):
        self.layout.addWidget(widget)