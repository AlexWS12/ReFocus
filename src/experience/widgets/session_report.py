from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget,
)
from PySide6.QtCore import Qt

from src.experience.widgets.centered_label import CenteredLabel


def _fmt_duration(seconds: int) -> str:
    if seconds is None:
        seconds = 0
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


class _ScoreRing(QFrame):
    # Large centred score with a coloured border ring

    def __init__(self, score: int, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(160, 160)

        color = self._score_color(score)

        self.setStyleSheet(
            f"QFrame#statCard {{ border: 4px solid {color}; border-radius: 80px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        num = QLabel(str(score))
        num.setAlignment(Qt.AlignCenter)
        num.setStyleSheet(f"font-size: 42px; font-weight: bold; color: {color}; border: none;")
        layout.addWidget(num)

        caption = QLabel("Focus Score")
        caption.setAlignment(Qt.AlignCenter)
        caption.setStyleSheet("font-size: 12px; color: #888; border: none;")
        layout.addWidget(caption)

    @staticmethod
    def _score_color(score: int) -> str:
        if score >= 80:
            return "#27ae60"
        if score >= 60:
            return "#f5a623"
        return "#e74c3c"


class _StatCard(QFrame):
    # Small metric card: title on top, value below

    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(CenteredLabel(title))
        layout.addWidget(CenteredLabel(value, secondary=True))


class _DistractionRow(QWidget):
    # Single row in the distraction breakdown: label · count · time

    def __init__(self, label: str, count: int, time_s: int, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 2, 8, 2)

        name = QLabel(label)
        name.setStyleSheet("font-size: 13px;")
        row.addWidget(name)

        row.addStretch()

        badge = QLabel(f"{count}x")
        badge.setStyleSheet("font-size: 13px; font-weight: bold;")
        row.addWidget(badge)

        dur = QLabel(_fmt_duration(time_s))
        dur.setObjectName("secondaryLabel")
        dur.setStyleSheet("font-size: 13px; margin-left: 8px;")
        row.addWidget(dur)


class SessionReport(QWidget):
    # Post-session report shown inside the Session page after stopping

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setAlignment(Qt.AlignTop)

    def load(self, report: dict, feedback: str = ""):
        self._clear()

        score = report.get("score", 0) or 0
        duration = report.get("duration", 0) or 0
        focused = report.get("focused_time", 0) or 0
        distracted = report.get("distraction_time", 0) or 0
        focus_pct = report.get("focus_percentage", 0) or 0
        xp = report.get("points_earned", 0) or 0
        coins = report.get("coins_earned", 0) or 0
        events = report.get("events", 0) or 0

        title = CenteredLabel("Session Complete")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self._root.addWidget(title)
        self._root.addSpacing(8)

        # --- Score ring centred ---
        score_row = QHBoxLayout()
        score_row.setAlignment(Qt.AlignCenter)
        score_row.addWidget(_ScoreRing(score))
        self._root.addLayout(score_row)
        self._root.addSpacing(32)

        # --- Key stats grid ---
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(_StatCard("Duration", _fmt_duration(duration)), 0, 0)
        grid.addWidget(_StatCard("Focused Time", _fmt_duration(focused)), 0, 1)
        grid.addWidget(_StatCard("Focus %", f"{focus_pct:.2f}%"), 0, 2)
        grid.addWidget(_StatCard("XP Earned", f"+{xp}"), 1, 0)
        grid.addWidget(_StatCard("Coins Earned", f"+{coins}"), 1, 1)
        grid.addWidget(_StatCard("Distractions", str(events)), 1, 2)
        self._root.addLayout(grid)
        self._root.addSpacing(12)

        # --- Distraction breakdown ---
        breakdown = self._build_breakdown(report, distracted)
        if breakdown is not None:
            self._root.addWidget(breakdown)

        # --- Brief feedback ---
        if feedback:
            self._root.addSpacing(8)
            fb_card = QFrame()
            fb_card.setObjectName("statCard")
            fb_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            fb_layout = QVBoxLayout(fb_card)
            fb_label = QLabel(feedback)
            fb_label.setWordWrap(True)
            fb_label.setAlignment(Qt.AlignLeft)
            fb_label.setStyleSheet("font-size: 13px; padding: 4px;")
            fb_layout.addWidget(fb_label)
            self._root.addWidget(fb_card)

    def _build_breakdown(self, report: dict, total_distracted: int) -> QFrame | None:
        rows = [
            ("Phone", report.get("phone_distractions", 0), None),
            ("Looked Away", report.get("look_away_distractions", 0), report.get("look_away_time", 0)),
            ("Left Desk", report.get("left_desk_distractions", 0), report.get("time_away", 0)),
            ("App", report.get("app_distractions", 0), None),
            ("Idle", report.get("idle_distractions", 0), None),
        ]
        rows = [(l, c or 0, t or 0) for l, c, t in rows if (c or 0) > 0]
        if not rows:
            return None

        card = QFrame()
        card.setObjectName("statCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(card)

        header = CenteredLabel("Distraction Breakdown")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        for label, count, time_s in rows:
            layout.addWidget(_DistractionRow(label, count, time_s))

        if total_distracted:
            total = CenteredLabel(f"Total distracted: {_fmt_duration(total_distracted)}", secondary=True)
            layout.addWidget(total)

        return card

    def _clear(self):
        while self._root.count():
            item = self._root.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
