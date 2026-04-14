from PySide6.QtWidgets import QWidget, QHBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.pet_catalog import PET_CATALOG, DEFAULT_PET


class PetView(QWidget):
    def __init__(self, parent=None, size: int = 120):
        super().__init__(parent)
        self._size = size

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.label = CenteredLabel("")
        self.layout.addWidget(self.label)

        self.refresh()

        app = QApplication.instance()
        if hasattr(app, "signals"):
            app.signals.pet_appearance_changed.connect(self.refresh)

    def refresh(self):
        from src.intelligence.pet_manager import PetManager

        mgr = PetManager()
        pet_id = mgr.get_active_pet()
        pet_info = PET_CATALOG.get(pet_id, PET_CATALOG[DEFAULT_PET])

        pixmap = QPixmap(pet_info["sprite"])
        scaled = pixmap.scaled(
            self._size, self._size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.label.setPixmap(scaled)
