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
            field.setFixedWidth(110)

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


class DetectionThresholdsPanel(QFrame):
    """Editable fields for phone-detection and gaze-angle thresholds.

    Loads saved values from settings.json on init. Uncalibrated phone
    fields show placeholder text. Values are read via get_thresholds()
    and persisted when the Settings page Apply button is clicked.
    """

    _PHONE_FIELDS = [
        ("yolo_conf", "YOLO confidence"),
        ("few_shot_similarity", "Appearance similarity"),
        ("fallback_conf", "Fallback confidence"),
    ]
    _GAZE_FIELDS = [
        ("yaw_threshold_deg", "Yaw (left/right) °"),
        ("pitch_threshold_deg", "Pitch (up/down) °"),
        ("roll_threshold_deg", "Roll (tilt) °"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        outer.addWidget(CenteredLabel("Detection thresholds"))

        saved = settings_manager.detection_thresholds()
        self.fields: dict[str, QLineEdit] = {}

        phone_label = QLabel("Phone detection")
        phone_label.setStyleSheet("font-weight: bold;")
        outer.addWidget(phone_label)
        for key, label_text in self._PHONE_FIELDS:
            self._add_field(outer, key, label_text, saved, placeholder="Run calibration")

        gaze_label = QLabel("Gaze / attention")
        gaze_label.setStyleSheet("font-weight: bold;")
        outer.addWidget(gaze_label)
        for key, label_text in self._GAZE_FIELDS:
            self._add_field(outer, key, label_text, saved, placeholder="degrees")

    def _add_field(self, layout, key, label_text, saved, placeholder):
        row = QHBoxLayout()
        row.setSpacing(10)
        name = QLabel(label_text, self)
        field = QLineEdit(self)
        field.setPlaceholderText(placeholder)
        field.setFixedWidth(110)
        value = saved.get(key)
        if value is not None:
            field.setText(str(value))
        row.addWidget(name, stretch=1)
        row.addWidget(field, stretch=0)
        layout.addLayout(row)
        self.fields[key] = field

    def get_thresholds(self) -> dict[str, float | None]:
        """Return current field values, preserving None for empty phone fields."""
        defaults = settings_manager.detection_thresholds()
        result: dict[str, float | None] = {}
        for key, field in self.fields.items():
            text = field.text().strip()
            if not text:
                result[key] = None
            else:
                try:
                    result[key] = float(text)
                except (ValueError, TypeError):
                    result[key] = defaults.get(key)
        return result


class DistractionCountSecondsPanel(DistractionPerTypeFieldsPanel):
    """Seconds before each distraction type starts counting (skeleton)."""

    def __init__(self, parent=None):
        super().__init__("Seconds before distraction counts", "Seconds", parent)

    @property
    def count_seconds_fields(self) -> dict[DistractionType, QLineEdit]:
        return self.fields
