from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.experience.mainWindow import MainWindow
from src.experience.petWindow import petWindow
from src.core.database_reader import DatabaseReader

class QApplication(QApplication):
    def __init__(self):
        super().__init__()

        # initialize stats reader
        self.database_reader = DatabaseReader()

        self.main_window = MainWindow()
        self.main_window.show()

        self.open_pet_window()
        QTimer.singleShot(0, self.position_pet_window)

    def run(self):
        self.exec()

    def open_pet_window(self):
        self.pet_window = petWindow()

    def position_pet_window(self):
        if not hasattr(self, 'pet_window') or not self.pet_window.isVisible():
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        pw = self.pet_window.width()
        ph = self.pet_window.height()
        margin = 10
        x = rect.right() - pw - margin
        y = rect.bottom() - ph - margin
        self.pet_window.move(x, y)