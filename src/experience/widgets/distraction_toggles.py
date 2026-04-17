from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QVBoxLayout

from src.core import settings_manager
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.distraction_list import DISTRACTION_LABELS
from src.intelligence.session_manager import DistractionType


class DistractionToggles(QFrame):
    # Checkboxes for which distraction types the user wants tracked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        outer.addWidget(CenteredLabel("Distraction tracking"))

        saved_enabled = settings_manager.enabled_distractions()

        self.checks: dict[DistractionType, QCheckBox] = {}
        for dtype in DistractionType:
            label = DISTRACTION_LABELS.get(dtype.value, dtype.value.replace("_", " ").title())
            cb = QCheckBox(label)
            cb.setChecked(dtype in saved_enabled)
            self.checks[dtype] = cb
            outer.addWidget(cb)

    def get_enabled_types(self) -> set[DistractionType]:
        # Return the set of distraction types currently checked
        return {dtype for dtype, cb in self.checks.items() if cb.isChecked()}

    def set_enabled_types(self, enabled: set[DistractionType]) -> None:
        # Update checkboxes to match the given set
        for dtype, cb in self.checks.items():
            cb.setChecked(dtype in enabled)
