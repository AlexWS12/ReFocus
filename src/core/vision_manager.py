from PySide6.QtCore import QObject, QTimer, Signal

from src.core import settings_manager
from src.vision.camera import Camera
from src.vision.detectors.phone_calibration import PhoneCalibration
from src.vision.Trackers.gaze_calibration import GazeCalibrator


class VisionManager(QObject):
    """Owns camera lifecycle and emits annotated frames to UI consumers.

    Two operating modes:
    - **Preview**: camera runs without distraction logging (Setup page).
    - **Session**: camera runs with a SessionManager so distractions are
      recorded in the database.  Preview stop calls are ignored while a
      session is active.
    """

    frame_ready = Signal(object)
    stream_state_changed = Signal(bool)
    distraction_started = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._session_active = False

    @property
    def is_running(self) -> bool:
        return self._camera is not None and self._timer.isActive()

    # ------------------------------------------------------------------
    # Preview (Setup page camera feed, no distraction logging)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the camera for preview. No-op if a session is active."""
        if self._session_active:
            return
        if self._camera is None:
            self._camera = Camera(camera_index=settings_manager.camera_index())
        if not self._timer.isActive():
            self._timer.start(30)
            self.stream_state_changed.emit(True)

    def stop(self) -> None:
        """Stop the preview camera. No-op if a session is active."""
        if self._session_active:
            return
        self._force_stop()

    # ------------------------------------------------------------------
    # Session (camera + distraction logging to database)
    # ------------------------------------------------------------------

    def start_session(self, session_manager) -> None:
        """Start the camera with distraction logging for an active study session."""
        self._force_stop()
        self._session_active = True
        self._camera = Camera(session_manager=session_manager, camera_index=settings_manager.camera_index())
        self._camera._on_distraction_started = self._on_camera_distraction
        self._timer.start(30)
        self.stream_state_changed.emit(True)

    def _on_camera_distraction(self, distraction_type: str) -> None:
        """Bridge callback from Camera thread to Qt signal."""
        self.distraction_started.emit(distraction_type)

    def stop_session(self) -> None:
        """Stop the camera when a session ends (flushes open distractions)."""
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
            return PhoneCalibration().run_calibration(target_detections=target_detections, camera_index=settings_manager.camera_index())
        finally:
            if was_running:
                self.start()

    def run_gaze_calibration(self) -> dict:
        was_running = self.is_running
        if was_running:
            self._force_stop()
        try:
            return GazeCalibrator().run(camera_index=settings_manager.camera_index())
        finally:
            if was_running:
                self.start()
