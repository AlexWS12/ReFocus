from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from src.experience.widgets.centered_label import CenteredLabel
from src.experience.button import Button
from src.core.qApplication import QApplication
from src.experience.widgets.vision_stream import VisionStream
from src.vision.camera_devices import list_cameras

class Setup(QWidget):
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setObjectName("pageRoot")

        self.app = QApplication.instance()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Camera selector
        camera_row = QHBoxLayout()
        camera_label = QLabel("Camera:")
        camera_label.setObjectName("secondaryLabel")
        self.camera_combo = QComboBox()
        self.camera_combo.setObjectName("cameraCombo")
        self._populate_cameras()
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        camera_row.addWidget(camera_label)
        camera_row.addWidget(self.camera_combo, 1)
        self.layout.addLayout(camera_row)

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

    def _populate_cameras(self) -> None:
        # Discover available cameras and fill the combo box
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        cameras = list_cameras()
        for cam in cameras:
            self.camera_combo.addItem(cam["name"], cam["index"])
        # Pre-select the currently active camera index
        current = self.app.vision_manager.camera_index
        for i in range(self.camera_combo.count()):
            if self.camera_combo.itemData(i) == current:
                self.camera_combo.setCurrentIndex(i)
                break
        self.camera_combo.blockSignals(False)

    def _on_camera_changed(self, combo_index: int) -> None:
        # Switch the vision pipeline to the newly selected camera
        if combo_index < 0:
            return
        device_index = self.camera_combo.itemData(combo_index)
        self.app.vision_manager.set_camera_index(device_index)

    def showEvent(self, event):
        super().showEvent(event)
        self._populate_cameras()
        self.vision_stream.start_stream()

    def hideEvent(self, event):
        self.vision_stream.stop_stream()
        super().hideEvent(event)

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
