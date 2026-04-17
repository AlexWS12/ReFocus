from PySide6.QtCore import QObject, QTimer, Signal

from src.vision.camera import Camera
from src.vision.detectors.phone_calibration import PhoneCalibration
from src.vision.Trackers.gaze_calibration import GazeCalibrator


class VisionManager(QObject):
    # Owns camera lifecycle and emits annotated frames to UI consumers

    frame_ready = Signal(object)
    stream_state_changed = Signal(bool)
    distraction_started = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._session_active = False
        self._camera_index: int = 0

    @property
    def camera_index(self) -> int:
        return self._camera_index

    @property
    def is_running(self) -> bool:
        return self._camera is not None and self._timer.isActive()

    def set_camera_index(self, index: int) -> None:
        # Change the active camera device
        if index == self._camera_index:
            return
        self._camera_index = index
        if self.is_running and not self._session_active:
            self._force_stop()
            self.start()

    # ------------------------------------------------------------------
    # Preview (Setup page camera feed, no distraction logging)
    # ------------------------------------------------------------------

    def start(self) -> None:
        # Start the camera for preview
        if self._session_active:
            return
        if self._camera is None:
            self._camera = Camera(camera_index=self._camera_index)
        if not self._timer.isActive():
            self._timer.start(30)
            self.stream_state_changed.emit(True)

    def stop(self) -> None:
        # Stop the preview camera
        if self._session_active:
            return
        self._force_stop()

    # ------------------------------------------------------------------
    # Session (camera + distraction logging to database)
    # ------------------------------------------------------------------

    def start_session(self, session_manager) -> None:
        # Start the camera with distraction logging for an active study session
        self._force_stop()
        self._session_active = True
        self._camera = Camera(session_manager=session_manager, camera_index=self._camera_index)
        self._camera._on_distraction_started = self._on_camera_distraction
        self._timer.start(30)
        self.stream_state_changed.emit(True)

    def _on_camera_distraction(self, distraction_type: str) -> None:
        # Bridge callback from Camera thread to Qt signal
        self.distraction_started.emit(distraction_type)

    def stop_session(self) -> None:
        # Stop the camera when a session ends (flushes open distractions)
        self._session_active = False
        self._force_stop()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _force_stop(self) -> None:
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

    # ------------------------------------------------------------------
    # Calibration (temporarily takes exclusive camera ownership)
    # ------------------------------------------------------------------

    def run_phone_calibration(self, target_detections: int = 15) -> dict:
        was_running = self.is_running
        if was_running:
            self._force_stop()
        try:
            return PhoneCalibration(camera_index=self._camera_index).run_calibration(target_detections=target_detections)
        finally:
            if was_running:
                self.start()

    def run_gaze_calibration(self) -> dict:
        was_running = self.is_running
        if was_running:
            self._force_stop()
        try:
            return GazeCalibrator(camera_index=self._camera_index).run()
        finally:
            if was_running:
                self.start()
