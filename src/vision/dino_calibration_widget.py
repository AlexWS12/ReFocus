# dino_calibration_widget.py
# PySide6 UI for the DINOv2 phone calibration flow.
# Guides the user through 3-4 capture steps, validates each photo,
# and calls DinoCalibration.build_prototype() when enough shots are accepted.

from __future__ import annotations

import sys
import cv2 as cv
import numpy as np

try:
    from PySide6.QtCore import Qt, QThread, Signal, QTimer
    from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QPalette
    from PySide6.QtWidgets import (
        QApplication,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QFrame,
        QSizePolicy,
        QProgressBar,
        QMessageBox,
    )
except ImportError as _e:
    raise ImportError(
        "PySide6 is required for the calibration UI. "
        "Install with: pip install PySide6"
    ) from _e

from dino_calibration import DinoCalibration, CAPTURE_STEPS


# ── camera worker thread ───────────────────────────────────────────────────────

class _CameraThread(QThread):
    """Continuously reads frames from the webcam and emits them as QImages."""

    frame_ready = Signal(np.ndarray)   # emits raw BGR numpy array

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self._camera_index = camera_index
        self._running = False

    def run(self) -> None:
        cap = cv.VideoCapture(self._camera_index)
        self._running = True
        while self._running:
            ret, frame = cap.read()
            if ret:
                self.frame_ready.emit(frame)
            self.msleep(33)   # ~30 fps
        cap.release()

    def stop(self) -> None:
        self._running = False
        self.wait(2000)


# ── helpers ────────────────────────────────────────────────────────────────────

def _bgr_to_pixmap(frame: np.ndarray, w: int, h: int) -> QPixmap:
    """Convert a BGR numpy frame to a scaled QPixmap."""
    rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
    rgb = cv.resize(rgb, (w, h), interpolation=cv.INTER_AREA)
    qimg = QImage(
        rgb.data, rgb.shape[1], rgb.shape[0],
        rgb.shape[1] * 3, QImage.Format.Format_RGB888,
    )
    return QPixmap.fromImage(qimg)


# ── main widget ────────────────────────────────────────────────────────────────

class DinoCalibrationWidget(QWidget):
    """
    Full-screen-friendly PySide6 widget for the DINOv2 calibration flow.

    Signals
    -------
    calibration_complete()   emitted when the prototype is successfully saved
    calibration_cancelled()  emitted when the user closes / cancels
    """

    calibration_complete = Signal()
    calibration_cancelled = Signal()

    # Preview dimensions inside the widget
    PREVIEW_W = 480
    PREVIEW_H = 360

    def __init__(self, model_path: str = "yolo26n.pt", camera_index: int = 0, parent=None):
        super().__init__(parent)
        self._calibrator = DinoCalibration(model_path)
        self._camera_index = camera_index

        # State
        self._current_step = 0          # index into CAPTURE_STEPS
        self._accepted_images: list[np.ndarray] = []
        self._per_step_embeddings: list = []  # one representative DINOv2 embedding per step
        self._latest_frame: np.ndarray | None = None
        self._min_photos = 3

        self._build_ui()
        self._start_camera()
        self._update_step_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle("Phone Calibration – DINOv2")
        self.setMinimumSize(600, 620)
        self._apply_dark_palette()

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 16, 20, 16)

        # Title
        title = QLabel("Phone Calibration")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        root.addWidget(title)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, len(CAPTURE_STEPS))
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat(f"  %v / {len(CAPTURE_STEPS)} photos")
        root.addWidget(self._progress)

        # Step label
        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sf = QFont()
        sf.setPointSize(11)
        sf.setBold(True)
        self._step_label.setFont(sf)
        root.addWidget(self._step_label)

        # Instruction label
        self._instruction_label = QLabel()
        self._instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._instruction_label.setWordWrap(True)
        self._instruction_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        root.addWidget(self._instruction_label)

        # Camera preview
        self._preview = QLabel()
        self._preview.setFixedSize(self.PREVIEW_W, self.PREVIEW_H)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #444; border-radius: 6px;"
        )
        self._preview.setText("Starting camera…")
        preview_wrap = QHBoxLayout()
        preview_wrap.addStretch()
        preview_wrap.addWidget(self._preview)
        preview_wrap.addStretch()
        root.addLayout(preview_wrap)

        # Validation feedback
        self._feedback = QLabel("")
        self._feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feedback.setWordWrap(True)
        self._feedback.setStyleSheet("font-size: 11px; color: #ff6b6b;")
        self._feedback.setMinimumHeight(36)
        root.addWidget(self._feedback)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._capture_btn = QPushButton("Capture Photo")
        self._capture_btn.setFixedHeight(40)
        self._capture_btn.setStyleSheet(
            "QPushButton { background-color: #2d6a9f; color: white; border-radius: 5px; font-size: 13px; }"
            "QPushButton:hover { background-color: #3880bb; }"
            "QPushButton:disabled { background-color: #3a3a3a; color: #666; }"
        )
        self._capture_btn.clicked.connect(self._on_capture)

        self._done_btn = QPushButton("Build Prototype")
        self._done_btn.setFixedHeight(40)
        self._done_btn.setEnabled(False)
        self._done_btn.setStyleSheet(
            "QPushButton { background-color: #2e7d32; color: white; border-radius: 5px; font-size: 13px; }"
            "QPushButton:hover { background-color: #388e3c; }"
            "QPushButton:disabled { background-color: #3a3a3a; color: #666; }"
        )
        self._done_btn.clicked.connect(self._on_build_prototype)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #555; color: white; border-radius: 5px; }"
            "QPushButton:hover { background-color: #666; }"
        )
        cancel_btn.clicked.connect(self._on_cancel)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._capture_btn)
        btn_row.addWidget(self._done_btn)
        root.addLayout(btn_row)

    def _apply_dark_palette(self) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#252525"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#e0e0e0"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    # ── camera ─────────────────────────────────────────────────────────────────

    def _start_camera(self) -> None:
        self._cam_thread = _CameraThread(self._camera_index, parent=self)
        self._cam_thread.frame_ready.connect(self._on_frame)
        self._cam_thread.start()

    def _on_frame(self, frame: np.ndarray) -> None:
        self._latest_frame = frame
        px = _bgr_to_pixmap(frame, self.PREVIEW_W, self.PREVIEW_H)
        self._preview.setPixmap(px)

    # ── step UI update ─────────────────────────────────────────────────────────

    def _update_step_ui(self) -> None:
        accepted = len(self._accepted_images)
        self._progress.setValue(accepted)

        if self._current_step < len(CAPTURE_STEPS):
            step = CAPTURE_STEPS[self._current_step]
            self._step_label.setText(step["label"])
            self._instruction_label.setText(step["instruction"])
            self._capture_btn.setEnabled(True)
        else:
            self._step_label.setText("All photos captured!")
            self._instruction_label.setText(
                "Review your photos below, then click 'Build Prototype' to finish."
            )
            self._capture_btn.setEnabled(False)

        # Enable 'Build Prototype' once minimum photos reached
        self._done_btn.setEnabled(accepted >= self._min_photos)

    def _set_feedback(self, text: str, success: bool = False) -> None:
        color = "#66bb6a" if success else "#ff6b6b"
        self._feedback.setStyleSheet(f"font-size: 11px; color: {color};")
        self._feedback.setText(text)

    # ── capture ────────────────────────────────────────────────────────────────

    def _on_capture(self) -> None:
        if self._latest_frame is None:
            self._set_feedback("Camera not ready – please wait.")
            return

        frame = self._latest_frame.copy()

        # Validate
        ok, reason = self._calibrator.validate_image(frame)
        if not ok:
            self._set_feedback(f"✗  {reason}")
            return

        # Compute representative embedding for diversity check
        try:
            crop = self._calibrator._extract_phone_crop(frame) or frame
            emb = self._calibrator.compute_embedding(crop)
            if emb is not None:
                # Diversity check against already-accepted images
                if self._per_step_embeddings:
                    ok_div, msg_div = DinoCalibration.check_diversity(
                        self._per_step_embeddings + [emb]
                    )
                    if not ok_div:
                        self._set_feedback(f"⚠  {msg_div}")
                        return
                self._per_step_embeddings.append(emb)
        except Exception:
            pass  # DINOv2 not available – skip diversity check

        self._accepted_images.append(frame)
        self._set_feedback(
            f"✓  Photo {len(self._accepted_images)} accepted.", success=True
        )

        # Advance to next step
        self._current_step += 1
        self._update_step_ui()

    # ── build prototype ────────────────────────────────────────────────────────

    def _on_build_prototype(self) -> None:
        self._capture_btn.setEnabled(False)
        self._done_btn.setEnabled(False)
        self._set_feedback("Building prototype… this may take a few seconds.", success=True)
        QApplication.processEvents()

        try:
            success = self._calibrator.build_prototype(self._accepted_images)
        except RuntimeError as exc:
            QMessageBox.critical(self, "Dependency Error", str(exc))
            self._capture_btn.setEnabled(True)
            self._done_btn.setEnabled(len(self._accepted_images) >= self._min_photos)
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to build prototype:\n{exc}")
            self._capture_btn.setEnabled(True)
            self._done_btn.setEnabled(len(self._accepted_images) >= self._min_photos)
            return

        self._cam_thread.stop()

        if success:
            self._set_feedback("✓  Prototype saved! Calibration complete.", success=True)
            QMessageBox.information(
                self,
                "Calibration Complete",
                "Your phone prototype has been saved.\n"
                "The detector will now use DINOv2 to verify detections.",
            )
            self.calibration_complete.emit()
        else:
            self._set_feedback("✗  Not enough valid embeddings. Please retake photos.")
            self._cam_thread.start()
            self._done_btn.setEnabled(len(self._accepted_images) >= self._min_photos)

    # ── cancel ─────────────────────────────────────────────────────────────────

    def _on_cancel(self) -> None:
        self._cam_thread.stop()
        self.calibration_cancelled.emit()
        self.close()

    def closeEvent(self, event) -> None:
        if hasattr(self, "_cam_thread") and self._cam_thread.isRunning():
            self._cam_thread.stop()
        super().closeEvent(event)


# ── standalone entry point ─────────────────────────────────────────────────────

def run_calibration_dialog(model_path: str = "yolo26n.pt", camera_index: int = 0) -> bool:
    """
    Launch the calibration widget as a standalone dialog.
    Returns True if calibration completed successfully.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    result = {"success": False}
    widget = DinoCalibrationWidget(model_path=model_path, camera_index=camera_index)
    widget.calibration_complete.connect(lambda: result.update({"success": True}))
    widget.calibration_complete.connect(widget.close)
    widget.show()
    app.exec()
    return result["success"]


if __name__ == "__main__":
    success = run_calibration_dialog()
    print("Calibration succeeded:", success)
