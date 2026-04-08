from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.button import Button
from src.core.qApplication import QApplication
from src.core import settings_manager
from src.experience.widgets.vision_stream import VisionStream

class Setup(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.app = QApplication.instance()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Camera selector
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Camera:")
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo, 1)
        self.layout.addLayout(camera_layout)

        self.vision_stream = VisionStream()
        self.layout.addWidget(self.vision_stream)

        self.calibrate_phone_btn = Button("Run Phone Calibration")
        self.calibrate_phone_btn.clicked.connect(self.calibrate_phone_detection)
        self.calibrate_gaze_btn = Button("Run Gaze Calibration")
        self.calibrate_gaze_btn.clicked.connect(self.calibrate_gaze_center)

        calibration_buttons_layout = QHBoxLayout()
        calibration_buttons_layout.addWidget(self.calibrate_phone_btn)
        calibration_buttons_layout.addWidget(self.calibrate_gaze_btn)
        self.layout.addLayout(calibration_buttons_layout)

        # add start session button to the layout
        start_btn = Button("Start Session")
        start_btn.setObjectName("startSessionButton")
        start_btn.clicked.connect(self.start_session)
        self.layout.addWidget(start_btn)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_camera_list()
        self.vision_stream.start_stream()

    def hideEvent(self, event):
        self.vision_stream.stop_stream()
        super().hideEvent(event)

    def _refresh_camera_list(self):
        """Populate the camera dropdown with available devices."""
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        cameras = settings_manager.available_cameras()
        saved_index = settings_manager.camera_index()
        select = 0
        for i, cam in enumerate(cameras):
            self.camera_combo.addItem(cam["name"], cam["index"])
            if cam["index"] == saved_index:
                select = i
        self.camera_combo.setCurrentIndex(select)
        self.camera_combo.blockSignals(False)

    def _on_camera_changed(self, combo_index: int):
        """Save the chosen camera and restart the preview stream."""
        if combo_index < 0:
            return
        device_index = self.camera_combo.itemData(combo_index)
        settings_manager.set_camera_index(device_index)
        self.vision_stream.stop_stream()
        self.vision_stream.start_stream()

    def calibrate_phone_detection(self):
        self.calibrate_phone_btn.setEnabled(False)
        self.calibrate_gaze_btn.setEnabled(False)
        self.app.vision_manager.run_phone_calibration(target_detections=15)
        self.calibrate_phone_btn.setEnabled(True)
        self.calibrate_gaze_btn.setEnabled(True)

    def calibrate_gaze_center(self):
        self.calibrate_phone_btn.setEnabled(False)
        self.calibrate_gaze_btn.setEnabled(False)
        self.app.vision_manager.run_gaze_calibration()
        self.calibrate_phone_btn.setEnabled(True)
        self.calibrate_gaze_btn.setEnabled(True)

    def start_session(self):
        self.app.session_manager.start_session()
        self.app.vision_manager.start_session(self.app.session_manager)
        self.app.main_window.pages_stack.setCurrentIndex(1)
        self.app.main_window.hide()
        self.app.pet_window.show()
        self.app.position_pet_window()
