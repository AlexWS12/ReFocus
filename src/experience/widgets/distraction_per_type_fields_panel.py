from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from src.core import settings_manager
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.distraction_list import DISTRACTION_LABELS
from src.intelligence.session_manager import DistractionType


class DistractionPerTypeFieldsPanel(QFrame):
    """One labeled text field per distraction type (skeleton — not wired to logic yet)."""

    def __init__(self, title: str, field_placeholder: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        outer.addWidget(CenteredLabel(title))

        self.fields: dict[DistractionType, QLineEdit] = {}
        for dtype in DistractionType:
            label_text = DISTRACTION_LABELS.get(
                dtype.value, dtype.value.replace("_", " ").title()
            )
            row = QHBoxLayout()
            row.setSpacing(10)

            name = QLabel(label_text, self)
            field = QLineEdit(self)
            field.setPlaceholderText(field_placeholder)
            field.setFixedWidth(88)

            row.addWidget(name, stretch=1)
            row.addWidget(field, stretch=0)
            outer.addLayout(row)
            self.fields[dtype] = field


class DistractionImportancePanel(DistractionPerTypeFieldsPanel):
    def __init__(self, parent=None):
        super().__init__("Distraction importance", "0.0 – 1.0", parent)
        saved = settings_manager.distraction_weights()
        for dtype, field in self.fields.items():
            field.setText(str(saved[dtype]))

    def get_weights(self) -> dict[DistractionType, float]:
        """Return current field values as floats, falling back to saved defaults."""
        saved = settings_manager.distraction_weights()
        result: dict[DistractionType, float] = {}
        for dtype, field in self.fields.items():
            try:
                result[dtype] = float(field.text())
            except (ValueError, TypeError):
                result[dtype] = saved[dtype]
        return result


class DistractionThresholdPanel(DistractionPerTypeFieldsPanel):
    def __init__(self, parent=None):
        super().__init__("Distraction threshold", "Threshold", parent)

    @property
    def threshold_fields(self) -> dict[DistractionType, QLineEdit]:
        return self.fields


class DistractionCountSecondsPanel(DistractionPerTypeFieldsPanel):
    """Seconds before each distraction type starts counting (skeleton)."""

    def __init__(self, parent=None):
        super().__init__("Seconds before distraction counts", "Seconds", parent)

    @property
    def count_seconds_fields(self) -> dict[DistractionType, QLineEdit]:
        return self.fields
