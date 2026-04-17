import random

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QGraphicsOpacityEffect
from PySide6.QtCore import QEvent, QTimer, Qt, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QPainter, QPainterPath, QColor
from src.core.qApplication import QApplication
from src.experience.button import Button
from src.experience.widgets.centered_label import CenteredLabel

from src.experience.widgets.pet_view import PetView
from src.experience.widgets.calendar import Calendar
from src.experience.widgets.score_trend import ScoreTrend
from src.experience.widgets.previous_session import PreviousSession

_EASTER_EGG_REQUIRED_CLICKS = 10
_EASTER_EGG_CLICK_WINDOW_MS = 650
_EASTER_EGG_BUBBLE_MS = 3000

# Mock list for random pet names. Edit these strings anytime.
_MOCK_PET_NAMES = [
    "Alex Waisman",
    "Alex Vutov",
    "Jonathan Serrano",
    "Jorge Taban",
    "Eduardo Goncalvez",
    "Paul Piotrowski",
    "Paul Allain",
    "Luis Delgado",
    "Christopher Belizaire",
    "Chaintainya Raj",
    "Josue Guerra",
    "Nickolas Garcia",
]


class DashboardSpeechBubble(QWidget):
    # Lightweight speech bubble with a short pop/fade animation

    TAIL_H = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._label = CenteredLabel("")
        self._label.setParent(self)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            "color: #ffffff; background: transparent; font-size: 12px; "
            "font-weight: 600; padding: 6px 10px;"
        )

        self._bg_color = QColor("#3b7deb")
        self._border_color = QColor("#2f69c7")
        self._text_color = QColor("#ffffff")

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade_out)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_in.setDuration(180)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_out.setDuration(220)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self.hide)

        self._float_in = QPropertyAnimation(self, b"pos", self)
        self._float_in.setDuration(180)
        self._float_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.hide()

    def _apply_theme_colors(self):
        is_dark = self.palette().color(self.palette().ColorRole.Window).lightness() < 90
        if is_dark:
            self._bg_color = QColor("#4f8ef7")
            self._border_color = QColor("#7fb0fa")
            self._text_color = QColor("#ffffff")
        else:
            self._bg_color = QColor("#3b7deb")
            self._border_color = QColor("#2f69c7")
            self._text_color = QColor("#ffffff")

        self._label.setStyleSheet(
            f"color: {self._text_color.name()}; background: transparent; font-size: 12px; "
            "font-weight: 600; padding: 6px 10px;"
        )

    def set_message(self, text: str):
        self._label.setText(text)
        self._label.adjustSize()

        bubble_w = max(self._label.width() + 10, 110)
        bubble_h = self._label.height() + 8 + self.TAIL_H
        self.setFixedSize(bubble_w, bubble_h)
        self._label.setGeometry(5, 2, bubble_w - 10, bubble_h - self.TAIL_H - 4)

    def show_at(self, x: int, y: int, visible_ms: int):
        self._apply_theme_colors()
        self._hide_timer.stop()
        self._fade_in.stop()
        self._fade_out.stop()
        self._float_in.stop()

        start_pos = QPoint(x, y + 10)
        end_pos = QPoint(x, y)
        self.move(start_pos)

        self._opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        self._float_in.setStartValue(start_pos)
        self._float_in.setEndValue(end_pos)
        self._float_in.start()

        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()

        self._hide_timer.start(visible_ms)

    def _start_fade_out(self):
        self._fade_out.stop()
        self._fade_out.setStartValue(self._opacity_effect.opacity())
        self._fade_out.setEndValue(0.0)
        self._fade_out.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self._border_color)
        painter.setBrush(self._bg_color)

        bubble_rect = self.rect().adjusted(0, 0, 0, -self.TAIL_H)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, 10, 10)

        tail_x = self.width() // 2
        tail_top = bubble_rect.bottom()
        path.moveTo(tail_x - 7, tail_top)
        path.lineTo(tail_x, tail_top + self.TAIL_H)
        path.lineTo(tail_x + 7, tail_top)

        painter.drawPath(path)
        painter.end()

class Dashboard(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.app = QApplication.instance()

        self.data = self.app.database_reader.load_dashboard_data()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.score_trend = ScoreTrend(self)
        self.grid_layout.addWidget(self.score_trend, 0, 0)

        self.PetView = PetView(self)
        self.grid_layout.addWidget(self.PetView, 0, 1)
        self.PetView.label.setCursor(Qt.CursorShape.PointingHandCursor)

        self.pet_name_bubble = DashboardSpeechBubble(self)

        self._pet_click_count = 0
        self._pet_click_reset_timer = QTimer(self)
        self._pet_click_reset_timer.setSingleShot(True)
        self._pet_click_reset_timer.timeout.connect(self._reset_pet_click_streak)

        self.PetView.label.installEventFilter(self)

        self.Calendar = Calendar(self)
        self.grid_layout.addWidget(self.Calendar, 1, 0)

        self.PreviousSession = PreviousSession(self)
        self.grid_layout.addWidget(self.PreviousSession, 1, 1)

        start_btn = Button("Start Session")
        start_btn.setObjectName("startSessionButton")
        start_btn.clicked.connect(self.start_setup)
        self.layout.addWidget(start_btn)

    def showEvent(self, event):
        super().showEvent(event)
        self.data = self.app.database_reader.load_dashboard_data()
        self.score_trend.refresh(self.data)
        self.PreviousSession.refresh(self.data)
        self.Calendar.set_scores(self.data.get("scores_by_date", {}))
        self.PetView.refresh()

    def start_setup(self):
        self.app.main_window.pages_stack.setCurrentIndex(6)

    def eventFilter(self, watched, event):
        if watched == self.PetView.label and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._pet_click_count += 1
                self._pet_click_reset_timer.start(_EASTER_EGG_CLICK_WINDOW_MS)

                if self._pet_click_count >= _EASTER_EGG_REQUIRED_CLICKS:
                    self._trigger_pet_name_easter_egg()
                    self._reset_pet_click_streak()
                return True

        return super().eventFilter(watched, event)

    def _reset_pet_click_streak(self):
        self._pet_click_count = 0

    def _trigger_pet_name_easter_egg(self):
        name = random.choice(_MOCK_PET_NAMES) if _MOCK_PET_NAMES else "Pet Name"
        self.pet_name_bubble.set_message(name)

        # Float the bubble above the pet card without affecting dashboard layout.
        pet_top_left = self.PetView.mapTo(self, self.PetView.rect().topLeft())
        bubble_x = pet_top_left.x() + (self.PetView.width() - self.pet_name_bubble.width()) // 2
        bubble_y = max(4, pet_top_left.y() - self.pet_name_bubble.height() - 6)
        self.pet_name_bubble.show_at(bubble_x, bubble_y, _EASTER_EGG_BUBBLE_MS)
    