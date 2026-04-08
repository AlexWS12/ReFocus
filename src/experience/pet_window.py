from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QEvent

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.pet_catalog import PET_CATALOG, DEFAULT_PET


class petWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Pet")

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self.label = CenteredLabel("")
        self._refresh_sprite()

        self.session_btn = QPushButton("Session")
        self.session_btn.setFixedHeight(24)
        self.session_btn.setStyleSheet(
            "background-color: #3b7deb; color: #fff; border: none; "
            "border-radius: 6px; font-size: 11px; padding: 2px 8px;"
        )
        self.session_btn.setCursor(Qt.PointingHandCursor)
        self.session_btn.clicked.connect(self._show_session)

        self.container = QWidget()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(4)
        self.container.setLayout(self.layout)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.session_btn)
        self.setCentralWidget(self.container)

        self.setFixedSize(100, 130)

        self.drag_position = None
        self.label.installEventFilter(self)
        self.label.setCursor(Qt.OpenHandCursor)

        app = QApplication.instance()
        if hasattr(app, "signals"):
            app.signals.pet_appearance_changed.connect(self._refresh_sprite)

    def _refresh_sprite(self):
        from src.intelligence.pet_manager import PetManager

        mgr = PetManager()
        pet_id = mgr.get_active_pet()
        pet_info = PET_CATALOG.get(pet_id, PET_CATALOG[DEFAULT_PET])

        pixmap = QPixmap(pet_info["sprite"])
        scaled = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

    def eventFilter(self, obj, event):
        if obj == self.label:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drag_position = event.globalPosition().toPoint()
                    self.label.setCursor(Qt.ClosedHandCursor)
                    return True
            elif event.type() == QEvent.MouseMove:
                if event.buttons() & Qt.LeftButton and self.drag_position is not None:
                    delta = event.globalPosition().toPoint() - self.drag_position
                    self.move(self.pos() + delta)
                    self.drag_position = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.drag_position = None
                    self.label.setCursor(Qt.OpenHandCursor)
                    return True
        return super().eventFilter(obj, event)

    def _show_session(self):
        app = QApplication.instance()
        app.main_window.pages_stack.setCurrentIndex(1)
        app.main_window.show()
        app.main_window.raise_()
