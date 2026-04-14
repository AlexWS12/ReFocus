from PySide6.QtWidgets import QApplication, QComboBox, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QVBoxLayout, QWidget

from src.core import settings_manager
from src.experience.button import Button
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.distraction_per_type_fields_panel import (
    DetectionThresholdsPanel,
    DistractionCountSecondsPanel,
    DistractionImportancePanel,
)
from src.experience.widgets.distraction_toggles import DistractionToggles
from src.intelligence.session_manager import DistractionType


class Settings(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(CenteredLabel("Settings"))

        # --- Profile selector ---
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(160)
        profile_row.addWidget(self.profile_combo)
        self.load_profile_btn = Button("Load")
        self.load_profile_btn.clicked.connect(self._load_selected_profile)
        profile_row.addWidget(self.load_profile_btn)
        self.save_profile_btn = Button("Save As...")
        self.save_profile_btn.clicked.connect(self._save_profile_as)
        profile_row.addWidget(self.save_profile_btn)
        self.delete_profile_btn = Button("Delete")
        self.delete_profile_btn.clicked.connect(self._delete_selected_profile)
        profile_row.addWidget(self.delete_profile_btn)
        profile_row.addStretch(1)
        self.layout.addLayout(profile_row)
        self._refresh_profile_combo()

        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.distraction_toggles = DistractionToggles(self)
        self.grid_layout.addWidget(self.distraction_toggles, 0, 0)

        self.distraction_importance_panel = DistractionImportancePanel(self)
        self.grid_layout.addWidget(self.distraction_importance_panel, 0, 1)

        self.detection_thresholds_panel = DetectionThresholdsPanel(self)
        self.grid_layout.addWidget(self.detection_thresholds_panel, 1, 0)

        self.distraction_count_seconds_panel = DistractionCountSecondsPanel(self)
        self.grid_layout.addWidget(self.distraction_count_seconds_panel, 1, 1)

        self.app = QApplication.instance()

        calibration_row = QHBoxLayout()
        self.calibrate_phone_btn = Button("Run Phone Calibration")
        self.calibrate_phone_btn.clicked.connect(self.calibrate_phone)
        calibration_row.addWidget(self.calibrate_phone_btn)

        self.calibrate_gaze_btn = Button("Run Gaze Calibration")
        self.calibrate_gaze_btn.clicked.connect(self.calibrate_gaze)
        calibration_row.addWidget(self.calibrate_gaze_btn)

        self.layout.addLayout(calibration_row)

        self.layout.addStretch(1)

        button_row = QHBoxLayout()

        self.dark_mode = Button("Change Theme")
        button_row.addWidget(self.dark_mode)
        self.dark_mode.clicked.connect(self.darkmode)

        self.apply_button = Button("Apply")
        self._apply_default_font = self.apply_button.font()
        button_row.addWidget(self.apply_button)
        self.apply_button.clicked.connect(self.apply_settings)

        self.layout.addLayout(button_row)

        # Connect field-change signals so the Apply button goes bold when
        # the UI state diverges from the persisted settings.
        for cb in self.distraction_toggles.checks.values():
            cb.toggled.connect(self._check_dirty)
        for field in self.distraction_importance_panel.fields.values():
            field.textChanged.connect(self._check_dirty)
        for field in self.detection_thresholds_panel.fields.values():
            field.textChanged.connect(self._check_dirty)

    def apply_settings(self):
        settings = settings_manager.load()
        enabled = self.distraction_toggles.get_enabled_types()
        settings["enabled_distractions"] = [dt.value for dt in enabled]
        weights = self.distraction_importance_panel.get_weights()
        settings["distraction_weights"] = {dt.value: w for dt, w in weights.items()}
        settings["detection_thresholds"] = self.detection_thresholds_panel.get_thresholds()
        settings_manager.save(settings)
        self._mark_clean()

    # --- Dirty-state tracking ---------------------------------------------------

    def _check_dirty(self):
        """Compare current UI values against saved settings; bold Apply if they differ."""
        saved = settings_manager.load()

        # Enabled distractions
        saved_enabled = set(saved.get("enabled_distractions", []))
        ui_enabled = {dt.value for dt in self.distraction_toggles.get_enabled_types()}
        if saved_enabled != ui_enabled:
            self._mark_dirty()
            return

        # Distraction weights
        saved_weights = saved.get("distraction_weights", {})
        ui_weights = {dt.value: w for dt, w in self.distraction_importance_panel.get_weights().items()}
        if saved_weights != ui_weights:
            self._mark_dirty()
            return

        # Detection thresholds
        saved_thresholds = saved.get("detection_thresholds", {})
        ui_thresholds = self.detection_thresholds_panel.get_thresholds()
        if saved_thresholds != ui_thresholds:
            self._mark_dirty()
            return

        self._mark_clean()

    def _mark_dirty(self):
        font = self.apply_button.font()
        font.setBold(True)
        self.apply_button.setFont(font)
        self.apply_button.setText("Apply *")

    def _mark_clean(self):
        font = self.apply_button.font()
        font.setBold(False)
        self.apply_button.setFont(font)
        self.apply_button.setText("Apply")

    def calibrate_phone(self):
        self.calibrate_phone_btn.setEnabled(False)
        self.calibrate_gaze_btn.setEnabled(False)
        self.app.vision_manager.run_phone_calibration(target_detections=15)
        self._refresh_thresholds()
        self.calibrate_phone_btn.setEnabled(True)
        self.calibrate_gaze_btn.setEnabled(True)

    def calibrate_gaze(self):
        self.calibrate_phone_btn.setEnabled(False)
        self.calibrate_gaze_btn.setEnabled(False)
        self.app.vision_manager.run_gaze_calibration()
        self._refresh_thresholds()
        self.calibrate_phone_btn.setEnabled(True)
        self.calibrate_gaze_btn.setEnabled(True)

    def _refresh_thresholds(self):
        """Reload detection threshold fields from settings.json after calibration."""
        saved = settings_manager.detection_thresholds()
        for key, field in self.detection_thresholds_panel.fields.items():
            value = saved.get(key)
            field.setText(str(value) if value is not None else "")

    def _refresh_profile_combo(self):
        """Repopulate the profile dropdown from saved profiles."""
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        for name in settings_manager.list_profiles():
            self.profile_combo.addItem(name)
        # Restore selection if it still exists, else select active profile
        active = settings_manager.active_profile_name()
        target = current if self.profile_combo.findText(current) >= 0 else active
        if target:
            idx = self.profile_combo.findText(target)
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)

    def _load_selected_profile(self):
        """Populate all settings fields from the selected profile."""
        name = self.profile_combo.currentText()
        if not name:
            return
        profile = settings_manager.load_profile(name)
        if profile is None:
            return

        # Thresholds
        thresholds = profile.get("detection_thresholds", {})
        for key, field in self.detection_thresholds_panel.fields.items():
            value = thresholds.get(key)
            field.setText(str(value) if value is not None else "")

        # Toggles
        enabled_raw = profile.get("enabled_distractions", [])
        enabled = {dt for dt in DistractionType if dt.value in enabled_raw}
        self.distraction_toggles.set_enabled_types(enabled)

        # Weights
        weights_raw = profile.get("distraction_weights", {})
        weights = {dt: weights_raw[dt.value] for dt in DistractionType if dt.value in weights_raw}
        self.distraction_importance_panel.set_weights(weights)

        settings_manager.save_profile(name, profile)  # marks active, no extra disk read

    def _save_profile_as(self):
        """Save current field values as a named profile, prompting for the name."""
        suggested = self.profile_combo.currentText() or ""
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:", text=suggested)
        if not ok or not name.strip():
            return
        name = name.strip()

        # Confirm before overwriting an existing profile
        if name in settings_manager.list_profiles():
            reply = QMessageBox.question(
                self,
                "Overwrite Profile",
                f'A profile named "{name}" already exists.\nOverwrite it?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        profile = {
            "detection_thresholds": self.detection_thresholds_panel.get_thresholds(),
            "enabled_distractions": [dt.value for dt in self.distraction_toggles.get_enabled_types()],
            "distraction_weights": {dt.value: w for dt, w in self.distraction_importance_panel.get_weights().items()},
        }
        settings_manager.save_profile(name, profile)
        self._refresh_profile_combo()

    def _delete_selected_profile(self):
        """Delete the currently selected profile."""
        name = self.profile_combo.currentText()
        if not name:
            return
        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f'Delete profile "{name}"? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        settings_manager.delete_profile(name)
        self._refresh_profile_combo()

    def darkmode(self):
        if self.app.style_path == "dark.qss":
            self.app.load_stylesheet("light.qss")
            self.app.style_path = "light.qss"
        else:
            self.app.load_stylesheet("dark.qss")
            self.app.style_path = "dark.qss"

            settings = settings_manager.load()
            settings["used_dark_mode"] = True
            settings_manager.save(settings)
