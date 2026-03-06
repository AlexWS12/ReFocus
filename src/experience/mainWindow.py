from PySide6.QtWidgets import QMainWindow
from src.experience.sideBar import Sidebar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Tracker Partner")

        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self.sidebar = Sidebar(self)
        self.setCentralWidget(self.sidebar)

        self.show()

