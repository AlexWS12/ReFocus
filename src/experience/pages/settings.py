from PySide6.QtWidgets import QApplication, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from src.core import settings_manager
from src.experience.button import Button
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.widgets.distraction_per_type_fields_panel import (
    DistractionCountSecondsPanel,
    DistractionImportancePanel,
    DistractionThresholdPanel,
)
from src.experience.widgets.distraction_toggles import DistractionToggles


class Settings(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(CenteredLabel("Settings"))

        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.distraction_toggles = DistractionToggles(self)
        self.grid_layout.addWidget(self.distraction_toggles, 0, 0)

        self.distraction_importance_panel = DistractionImportancePanel(self)
        self.grid_layout.addWidget(self.distraction_importance_panel, 0, 1)

        self.distraction_threshold_panel = DistractionThresholdPanel(self)
        self.grid_layout.addWidget(self.distraction_threshold_panel, 1, 0)

        self.distraction_count_seconds_panel = DistractionCountSecondsPanel(self)
        self.grid_layout.addWidget(self.distraction_count_seconds_panel, 1, 1)

        self.layout.addStretch(1)

        button_row = QHBoxLayout()

        self.dark_mode = Button("Change Theme")
        self.app = QApplication.instance()
        button_row.addWidget(self.dark_mode)
        self.dark_mode.clicked.connect(self.darkmode)

        self.apply_button = Button("Apply")
        button_row.addWidget(self.apply_button)
        self.apply_button.clicked.connect(self.apply_settings)

        self.layout.addLayout(button_row)

    def apply_settings(self):
        settings = settings_manager.load()
        enabled = self.distraction_toggles.get_enabled_types()
        settings["enabled_distractions"] = [dt.value for dt in enabled]
        weights = self.distraction_importance_panel.get_weights()
        settings["distraction_weights"] = {dt.value: w for dt, w in weights.items()}
        settings_manager.save(settings)

    def darkmode(self):
        if self.app.style_path == "dark.qss":
            self.app.load_stylesheet("light.qss")
            self.app.style_path = "light.qss"
        else:
            self.app.load_stylesheet("dark.qss")
            self.app.style_path = "dark.qss"
