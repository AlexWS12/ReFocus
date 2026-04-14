from PySide6.QtWidgets import QCalendarWidget
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCore import Qt, QRect, QDate


_GREEN = QColor(39, 174, 96, 90)
_YELLOW = QColor(245, 166, 35, 90)
_RED = QColor(231, 76, 60, 90)


def _score_color(score: float) -> QColor:
    if score >= 80:
        return _GREEN
    if score >= 60:
        return _YELLOW
    return _RED


class Calendar(QCalendarWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setMaximumWidth(280)
        self.setMaximumHeight(220)
        self._scores: dict[str, float] = {}

        scores_by_date = getattr(parent, "data", {}).get("scores_by_date", {})
        self.set_scores(scores_by_date)

    def set_scores(self, scores_by_date: dict[str, float]):
        self._scores = scores_by_date
        self.updateCells()

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        date_str = date.toString("yyyy-MM-dd")
        score = self._scores.get(date_str)

        if score is not None:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_score_color(score))
            margin = 2
            painter.drawRoundedRect(
                rect.adjusted(margin, margin, -margin, -margin), 4, 4,
            )
            painter.restore()

        super().paintCell(painter, rect, date)
