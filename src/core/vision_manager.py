from PySide6.QtCore import QObject, QTimer, Signal

from src.vision.camera import Camera
from src.vision.detectors.phone_calibration import PhoneCalibration
from src.vision.Trackers.gaze_calibration import GazeCalibrator


class VisionManager(QObject):
    """Owns camera lifecycle and emits annotated frames to UI consumers."""

    frame_ready = Signal(object)
    stream_state_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    @property
    def is_running(self) -> bool:
        return self._camera is not None and self._timer.isActive()

    def start(self) -> None:
        if self._camera is None:
            self._camera = Camera()
        if not self._timer.isActive():
            self._timer.start(30)  # ~30ms per update
            self.stream_state_changed.emit(True)

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self._camera is not None:
            self._camera.release()
            self._camera = None
        self.stream_state_changed.emit(False)

    def _tick(self) -> None:
        if self._camera is None:
            return
        data = self._camera.read_frame()
        if data is None:
            return
        _, annotated = data
        self.frame_ready.emit(annotated)

    def run_phone_calibration(self, target_detections: int = 15) -> dict:
        """Run phone calibration while temporarily owning the camera exclusively."""
        was_running = self.is_running
        if was_running:
            self.stop()
        try:
            return PhoneCalibration().run_calibration(target_detections=target_detections)
        finally:
            if was_running:
                self.start()

    def run_gaze_calibration(self) -> dict:
        """Run gaze calibration while temporarily owning the camera exclusively."""
        was_running = self.is_running
        if was_running:
            self.stop()
        try:
            return GazeCalibrator().run()
        finally:
            if was_running:
                self.start()
