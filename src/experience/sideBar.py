from src.experience.mainWindow import MainWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton

class Sidebar(QWidget):
    def __init__(self, main_window : MainWindow):
        super().__init__()
        self.main_window = main_window
        self.layout = QVBoxLayout() 
        self.setLayout(self.layout)

    def add_items(self, widget: QWidget):
        self.layout.addWidget(widget)