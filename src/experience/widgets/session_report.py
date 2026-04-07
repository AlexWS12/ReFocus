from datetime import datetime

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget,
)
from PySide6.QtCore import Qt, QMargins, QRectF
from PySide6.QtGui import QColor, QPainter, QPen

from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries,
    QHorizontalBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
)

from src.experience.widgets.centered_label import CenteredLabel

_FOCUS_COLOR = QColor("#27ae60")
_DISTRACT_COLOR = QColor("#e74c3c")

_BAR_COLORS = [
    QColor("#e74c3c"),
    QColor("#f5a623"),
    QColor("#3b7deb"),
    QColor("#9b59b6"),
    QColor("#8892a4"),
]

_TIMELINE_FOCUSED = QColor(39, 174, 96, 180)
_TIMELINE_DISTRACTED = QColor(231, 76, 60, 200)
_TIMELINE_BG = QColor(200, 200, 200, 60)


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
    """Large centred score with a coloured border ring."""

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
    """Small metric card: title on top, value below."""

    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(CenteredLabel(title))
        layout.addWidget(CenteredLabel(value, secondary=True))


class _FocusDonut(QFrame):
    """Donut chart showing focused vs distracted time split."""

    def __init__(self, focused: int, distracted: int, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(160, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        chart = QChart()
        chart.setBackgroundVisible(False)
        chart.legend().hide()
        chart.setMargins(QMargins(0, 0, 0, 0))

        series = QPieSeries()
        series.setHoleSize(0.55)

        f_slice = series.append("Focused", max(focused, 0))
        f_slice.setColor(_FOCUS_COLOR)
        f_slice.setBorderWidth(0)

        d_slice = series.append("Distracted", max(distracted, 0))
        d_slice.setColor(_DISTRACT_COLOR)
        d_slice.setBorderWidth(0)

        chart.addSeries(series)

        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(view)


class _SessionTimeline(QFrame):
    """Horizontal bar showing focused/distracted segments across session duration."""

    def __init__(self, start_time: str, duration: int, events_timeline: list, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(80)

        self._duration = max(duration, 1)
        self._start_time = start_time
        self._segments = self._build_segments(events_timeline)

    def _build_segments(self, events_timeline: list) -> list:
        """Convert event list into (start_frac, end_frac) distraction segments."""
        if not self._start_time:
            return []

        try:
            session_start = datetime.fromisoformat(self._start_time)
        except (ValueError, TypeError):
            return []

        segments = []
        for ev in events_timeline:
            try:
                ev_time = datetime.fromisoformat(ev["timestamp"])
            except (ValueError, TypeError):
                continue
            offset = (ev_time - session_start).total_seconds()
            dur = ev.get("duration", 0) or 0
            start_frac = max(0, offset / self._duration)
            end_frac = min(1.0, (offset + dur) / self._duration)
            if end_frac > start_frac:
                segments.append((start_frac, end_frac))
        return segments

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 12
        bar_h = 24
        x = margin
        y = (self.height() - bar_h) // 2
        w = self.width() - 2 * margin

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_TIMELINE_FOCUSED)
        painter.drawRoundedRect(QRectF(x, y, w, bar_h), 6, 6)

        painter.setBrush(_TIMELINE_DISTRACTED)
        for start_frac, end_frac in self._segments:
            sx = x + start_frac * w
            sw = (end_frac - start_frac) * w
            painter.drawRoundedRect(QRectF(sx, y, sw, bar_h), 4, 4)

        painter.setPen(QPen(QColor("#888"), 1))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            QRectF(x, y + bar_h + 2, w, 16),
            Qt.AlignLeft | Qt.AlignTop,
            "Start",
        )
        painter.drawText(
            QRectF(x, y + bar_h + 2, w, 16),
            Qt.AlignRight | Qt.AlignTop,
            _fmt_duration(self._duration),
        )

        painter.end()


def _build_distraction_bars(report: dict) -> QFrame | None:
    """Horizontal bar chart of per-type distraction counts for a single session."""
    rows = [
        ("Phone", report.get("phone_distractions", 0) or 0),
        ("Looked Away", report.get("look_away_distractions", 0) or 0),
        ("Left Desk", report.get("left_desk_distractions", 0) or 0),
        ("App", report.get("app_distractions", 0) or 0),
        ("Idle", report.get("idle_distractions", 0) or 0),
    ]
    rows = [(label, count) for label, count in rows if count > 0]
    if not rows:
        return None

    card = QFrame()
    card.setObjectName("statCard")
    card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    layout = QVBoxLayout(card)

    header = CenteredLabel("Distraction Breakdown")
    header.setStyleSheet("font-weight: bold; font-size: 14px;")
    layout.addWidget(header)

    chart = QChart()
    chart.setBackgroundVisible(False)
    chart.legend().hide()
    chart.setMargins(QMargins(4, 4, 4, 4))

    categories = []
    series = QHorizontalBarSeries()
    for i, (label, count) in enumerate(rows):
        bar_set = QBarSet(label)
        bar_set.append(count)
        bar_set.setColor(_BAR_COLORS[i % len(_BAR_COLORS)])
        series.append(bar_set)
        categories.append(label)

    chart.addSeries(series)

    axis_y = QBarCategoryAxis()
    axis_y.append(categories)
    chart.addAxis(axis_y, Qt.AlignLeft)
    series.attachAxis(axis_y)

    max_val = max(c for _, c in rows)
    axis_x = QValueAxis()
    axis_x.setRange(0, max_val * 1.15)
    axis_x.setLabelFormat("%d")
    axis_x.setGridLineColor(QColor(200, 200, 200, 60))
    chart.addAxis(axis_x, Qt.AlignBottom)
    series.attachAxis(axis_x)

    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setStyleSheet("background: transparent; border: none;")
    view.setMinimumHeight(max(100, len(rows) * 36))
    layout.addWidget(view)

    return card


class SessionReport(QWidget):
    """Post-session report shown inside the Session page after stopping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setAlignment(Qt.AlignTop)

    def load(self, report: dict):
        """Populate the report from a session_report() dict. Clears previous content."""
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

        hero_row = QHBoxLayout()
        hero_row.setAlignment(Qt.AlignCenter)
        hero_row.addWidget(_ScoreRing(score))
        hero_row.addSpacing(24)
        hero_row.addWidget(_FocusDonut(focused, distracted))
        self._root.addLayout(hero_row)
        self._root.addSpacing(16)

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

        bar_chart = _build_distraction_bars(report)
        if bar_chart is not None:
            self._root.addWidget(bar_chart)
            self._root.addSpacing(8)

        timeline_events = report.get("events_timeline", [])
        start_time = report.get("start_time", "")
        if duration > 0:
            timeline_label = CenteredLabel("Session Timeline")
            timeline_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            self._root.addWidget(timeline_label)
            self._root.addWidget(_SessionTimeline(start_time, duration, timeline_events))

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
