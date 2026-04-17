from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Signal, QObject
from PySide6.QtGui import QIcon

from src.experience.main_window import MainWindow
from src.experience.pet_window import petWindow
from src.core.database_reader import DatabaseReader
from src.core.vision_manager import VisionManager
from src.core import settings_manager
from src.intelligence.session_manager import SessionManager

from src.experience.achievement_manager import Achievement_Manager
from src.experience.widgets.achievement_catalog import ACHIEVMENT_CATALOG
from src.core import settings_manager

from pathlib import Path


class AppSignals(QObject):
    pet_appearance_changed = Signal()
    achievement_unlocked = Signal(str)


class QApplication(QApplication):
    def __init__(self):
        super().__init__()
        self.signals = AppSignals()

        icon_path = (
            Path(__file__).resolve().parent.parent
            / "experience"
            / "static"
            / "pets"
            / "cat"
            / "Cat.png"
        )
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        settings_manager.ensure_defaults()

        # Load global stylesheet
        self.load_stylesheet("light.qss")
        self.style_path = "light.qss"


        # initialize stats reader
        self.database_reader = DatabaseReader()
        self.vision_manager = VisionManager(self)
        self.session_manager = SessionManager()

        # kick off ML analysis in background immediately so it's ready
        # by the time the user opens the Report page
        self.database_reader.run_analysis_async()

        self.main_window = MainWindow()
        self.main_window.show()

        self.open_pet_window()
        QTimer.singleShot(0, self.position_pet_window)
        self.aboutToQuit.connect(self.vision_manager.stop_session)
        self.vision_manager.distraction_started.connect(self.pet_window.show_speech_bubble)

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

    def load_stylesheet(self, theme: str):
        style_path = (
            Path(__file__).resolve().parent.parent / "experience" / "style" / theme
        )
        if style_path.exists():
            self.setStyleSheet(style_path.read_text())

    def check_acheivement(self):
        settings = settings_manager.load()
        already_unlocked = set(settings.get("unlocked_achievements", []))
        
        manager = Achievement_Manager()
        progress = manager.get_progress()
        newly_unlocked = []
        
        for achievement, info in ACHIEVMENT_CATALOG.items():
            if progress[achievement] >= info["goal"] and achievement not in already_unlocked:
                self.signals.achievement_unlocked.emit(achievement)
                newly_unlocked.append(achievement)
        
        if newly_unlocked:
            settings["unlocked_achievements"] = list(already_unlocked | set(newly_unlocked))
            settings_manager.save(settings)

