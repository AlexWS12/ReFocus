from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from src.experience.pet_catalog import DEFAULT_PET, PET_CATALOG
from src.experience.widgets.pet_view import PetView
from src.intelligence.pet_manager import PetManager


class ReportPetWidget(QFrame):
    """Overlay widget with a pet and a left-side insight card."""
    layout_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._insight_index = -1

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.insight_card = QFrame()
        self.insight_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.insight_card.setStyleSheet(
            "QFrame {"
            "background-color: rgba(32, 42, 62, 175);"
            "border: 0.5px solid rgba(140, 166, 198, 120);"
            "border-radius: 10px;"
            "}"
        )
        self.insight_card.setFixedWidth(280)
        card_layout = QVBoxLayout(self.insight_card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(0)

        self.title = QLabel("Insight Buddy")
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #d4deef; "
            "background: transparent; border: none; margin-bottom: 2px;"
        )
        card_layout.addWidget(self.title)

        self.pet_view = PetView(self, size=88)
        pet_column = QWidget()
        pet_layout = QVBoxLayout(pet_column)
        pet_layout.setContentsMargins(0, 0, 0, 0)
        pet_layout.setSpacing(4)
        pet_layout.addWidget(self.pet_view, alignment=Qt.AlignCenter)

        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.message.setStyleSheet(
            "font-size: 12px; color: #d6e2f2; background: transparent; border: none;"
        )
        card_layout.addWidget(self.message)

        layout.addWidget(self.insight_card, alignment=Qt.AlignVCenter)
        layout.addWidget(pet_column, alignment=Qt.AlignBottom)

        self._card_opacity = QGraphicsOpacityEffect(self.insight_card)
        self._card_opacity.setOpacity(1.0)
        self.insight_card.setGraphicsEffect(self._card_opacity)

        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._fade_out_card)

        self._fade_anim = QPropertyAnimation(self._card_opacity, b"opacity", self)
        self._fade_anim.setDuration(800)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_finished)

    def refresh(self, report_data: dict):
        self.pet_view.refresh()
        self.title.setText(self._title_text())

        insights = (
            (report_data or {})
            .get("pattern_analysis", {})
            .get("insights", [])
        )
        self.message.setText(self._pick_message(insights, report_data or {}))
        self._reset_fade_timer()

    def _reset_fade_timer(self):
        self._fade_timer.stop()
        self._fade_anim.stop()
        self.insight_card.show()
        self._card_opacity.setOpacity(1.0)
        self.adjustSize()
        self.layout_changed.emit()
        self._fade_timer.start(10000)

    def _fade_out_card(self):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._card_opacity.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self):
        self.insight_card.hide()
        self.adjustSize()
        self.layout_changed.emit()

    def _title_text(self) -> str:
        pet_id = PetManager().get_active_pet()
        pet_name = PET_CATALOG.get(pet_id, PET_CATALOG[DEFAULT_PET]).get("name", "Your Pet")
        return f"{pet_name}'s Insight"

    def _pick_message(self, insights: list[str], report_data: dict) -> str:
        if insights:
            self._insight_index = (self._insight_index + 1) % len(insights)
            return insights[self._insight_index]

        analytics = report_data.get("session_analytics", {})
        total_sessions = analytics.get("total_sessions", 0) or 0
        total_focus = analytics.get("lifetime_focus_seconds", 0) or 0

        if total_sessions == 0:
            return "Start your first session and I will share personalized focus tips."
        if total_sessions < 10:
            return (
                f"I need {10 - total_sessions} more sessions to unlock deeper pattern insights. "
                "Keep going!"
            )
        if total_focus > 0:
            return "Nice momentum. Keep your strongest routine and protect your peak focus blocks."
        return "You're building data fast. I will keep learning from your sessions."
