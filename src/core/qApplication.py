from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.experience.main_window import MainWindow
from src.experience.pet_window import petWindow
from src.core.database_reader import DatabaseReader

from pathlib import Path

class QApplication(QApplication):
    def __init__(self):
        super().__init__()

        # Load global stylesheet
        style_path = Path(__file__).resolve().parent.parent / "experience" / "style" / "theme.qss"
        if style_path.exists():
            self.setStyleSheet(style_path.read_text())

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