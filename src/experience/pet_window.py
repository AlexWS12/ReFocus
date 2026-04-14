from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QApplication, QLabel
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PySide6.QtCore import Qt, QEvent, QTimer

from src.experience.widgets.centered_label import CenteredLabel
from src.experience.pet_catalog import PET_CATALOG, DEFAULT_PET

_BUBBLE_MESSAGES = {
    "PHONE_DISTRACTION": "Put your phone away!",
    "LOOK_AWAY_DISTRACTION": "Eyes on screen!",
    "LEFT_DESK_DISTRACTION": "Come back to your desk!",
}

_BUBBLE_COOLDOWN_SECS = 15


class SpeechBubble(QWidget):
    """Rounded speech-bubble tooltip that floats above the pet."""

    TAIL_H = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            "color: #fff; background: transparent; font-size: 11px; "
            "font-weight: 600; padding: 6px 10px;"
        )
        self._bg_color = QColor("#3b7deb")
        self.hide()

    def set_message(self, text: str):
        self._label.setText(text)
        self._label.adjustSize()
        w = self._label.width() + 4
        h = self._label.height() + 4 + self.TAIL_H
        self.setFixedSize(max(w, 80), h)
        self._label.setGeometry(2, 2, w - 4, h - 4 - self.TAIL_H)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bg_color)

        bubble_rect = self.rect().adjusted(0, 0, 0, -self.TAIL_H)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect.toRectF(), 8, 8)

        # small triangular tail pointing down toward the pet
        tail_x = self.width() // 2
        tail_top = bubble_rect.bottom()
        path.moveTo(tail_x - 6, tail_top)
        path.lineTo(tail_x, tail_top + self.TAIL_H)
        path.lineTo(tail_x + 6, tail_top)

        painter.drawPath(path)
        painter.end()


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

        self._bubble = SpeechBubble()
        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self._bubble.hide)
        self._last_bubble_time = 0.0

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

    def show_speech_bubble(self, distraction_type: str):
        """Display a speech bubble above the pet for the given distraction type.

        Ignores calls that arrive within _BUBBLE_COOLDOWN_SECS of the last
        bubble to avoid spamming the user.
        """
        if not self.isVisible():
            return

        import time
        now = time.time()
        if now - self._last_bubble_time < _BUBBLE_COOLDOWN_SECS:
            return
        self._last_bubble_time = now

        message = _BUBBLE_MESSAGES.get(distraction_type, "Stay focused!")
        self._bubble.set_message(message)

        pet_pos = self.pos()
        bw = self._bubble.width()
        bx = pet_pos.x() + (self.width() - bw) // 2
        by = pet_pos.y() - self._bubble.height() - 2
        self._bubble.move(bx, by)
        self._bubble.show()
        self._bubble.raise_()

        self._bubble_timer.start(5000)

    def _show_session(self):
        app = QApplication.instance()
        app.main_window.pages_stack.setCurrentIndex(1)
        app.main_window.show()
        app.main_window.raise_()
