from PySide6.QtWidgets import QApplication
from src.experience.mainWindow import MainWindow

class QApplication(QApplication):
    def __init__(self):
        super().__init__()
        self.main_window = MainWindow()
        self.main_window.show()

    def run(self):
        self.exec()