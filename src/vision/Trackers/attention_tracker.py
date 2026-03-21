# attention_tracker.py
# Face-facing-screen tracking using MediaPipe Face Landmarker.

import cv2 as cv
import mediapipe as mp
import os
import time
import json
import numpy as np

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision


class gazeTracker:
    """Tracks whether the user's face is oriented toward the screen."""

    def __init__(self, calibration_file: str | None = None):
        model_path = os.path.join(os.path.dirname(__file__), "face_landmarker.task")

        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            output_face_blendshapes=False,          # Blendshapes (smile, blink, etc.) not needed here.
            output_facial_transformation_matrixes=False,  # We compute head pose ourselves via solvePnP.
            num_faces=1,                            # Only track the primary user; ignore bystanders.
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)
        self.landmarks = None

        self.calibration_file = calibration_file or os.path.join(
            os.path.dirname(__file__), "gaze_center_calibration.json"
        )

        # Thresholds must be set before _load_attention_bounds() so they can
        # be used as fallback defaults when the calibration file is missing fields.
        # These values represent the maximum degrees of head rotation away from
        # screen center before the tracker classifies the user as "away".
        # Yaw (left/right) is most sensitive to phone distraction, so its threshold
        # is tighter than roll (head tilt), which rarely indicates true inattention.
        self.yaw_threshold_deg = 18.0
        self.pitch_threshold_deg = 15.0
        self.roll_threshold_deg = 22.0

        self.center_offsets = self._load_center_offsets()
        self.calibrated_bounds = self._load_attention_bounds()

        # Performance controls: do not run full face-landmarker on every frame.
        # The dual gate (frame_skip AND wall-clock) avoids overloading both slow
        # cameras (few frames to skip) and fast CPUs (many frames per second).
        self.frame_skip = 2  # Evaluate at most every Nth frame.
        self.detection_interval_seconds = 0.20  # Also cap by wall-clock (~5 Hz max updates).
        self.draw_pose_axes = False  # Axis rendering is useful for debug but costs extra compute.

        self._frame_counter = 0
        self._last_detection_ts = 0.0
        self._cached_data = {
            "face_present": False,
            "eyes_detected": False,
            "left_iris": None,
            "right_iris": None,
            "gaze_state_horizontal": "unknown",
            "gaze_state_vertical": "unknown",
            "yaw_deg": 0.0,
            "pitch_deg": 0.0,
            "roll_deg": 0.0,
            "face_facing_screen": False,
            "attention_state": "no_face",
        }

    def _load_center_offsets(self) -> dict:
        """Load persisted center offsets so attention is relative to the screen center, not camera position."""
        default_offsets = {"yaw_deg": 0.0, "pitch_deg": 0.0, "roll_deg": 0.0}
        if not os.path.exists(self.calibration_file):
            return default_offsets

        try:
            with open(self.calibration_file, "r", encoding="utf-8") as f:
                payload = json.load(f)

            # New profile format nests center offsets under "center_offsets".
            if isinstance(payload.get("center_offsets"), dict):
                center = payload["center_offsets"]
                return {
                    "yaw_deg": float(center.get("yaw_deg", 0.0)),
                    "pitch_deg": float(center.get("pitch_deg", 0.0)),
                    "roll_deg": float(center.get("roll_deg", 0.0)),
                }

            # Backward compatibility with the previous flat format.
            return {
                "yaw_deg": float(payload.get("yaw_deg", 0.0)),
                "pitch_deg": float(payload.get("pitch_deg", 0.0)),
                "roll_deg": float(payload.get("roll_deg", 0.0)),
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return default_offsets

    def _load_attention_bounds(self) -> dict | None:
        """Load calibrated yaw/pitch bounds produced by corner-based gaze calibration."""
        if not os.path.exists(self.calibration_file):
            return None

        try:
            with open(self.calibration_file, "r", encoding="utf-8") as f:
                payload = json.load(f)

            yaw_bounds = payload.get("yaw_bounds")
            pitch_bounds = payload.get("pitch_bounds")
            roll_threshold = payload.get("roll_threshold_deg")

            if not isinstance(yaw_bounds, dict) or not isinstance(pitch_bounds, dict):
                return None

            return {
                "yaw_min": float(yaw_bounds.get("min", -self.yaw_threshold_deg)),
                "yaw_max": float(yaw_bounds.get("max", self.yaw_threshold_deg)),
                "pitch_min": float(pitch_bounds.get("min", -self.pitch_threshold_deg)),
                "pitch_max": float(pitch_bounds.get("max", self.pitch_threshold_deg)),
                "roll_threshold_deg": float(roll_threshold if roll_threshold is not None else self.roll_threshold_deg),
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def set_center_offsets(self, yaw_deg: float, pitch_deg: float, roll_deg: float):
        """Apply new center offsets immediately and persist them for future runs."""
        self.center_offsets = {
            "yaw_deg": float(yaw_deg),
            "pitch_deg": float(pitch_deg),
            "roll_deg": float(roll_deg),
        }
        try:
            with open(self.calibration_file, "w", encoding="utf-8") as f:
                json.dump(self.center_offsets, f, indent=2)
        except OSError:
            # Best effort persistence; tracker still works with in-memory offsets.
            pass

    def set_calibration_profile(self, profile: dict):
        """Apply and persist full calibration profile (center + bounds)."""
        center = profile.get("center_offsets", {})
        self.center_offsets = {
            "yaw_deg": float(center.get("yaw_deg", 0.0)),
            "pitch_deg": float(center.get("pitch_deg", 0.0)),
            "roll_deg": float(center.get("roll_deg", 0.0)),
        }

        yaw_bounds = profile.get("yaw_bounds")
        pitch_bounds = profile.get("pitch_bounds")
        roll_threshold = profile.get("roll_threshold_deg")
        if isinstance(yaw_bounds, dict) and isinstance(pitch_bounds, dict):
            self.calibrated_bounds = {
                "yaw_min": float(yaw_bounds.get("min", -self.yaw_threshold_deg)),
                "yaw_max": float(yaw_bounds.get("max", self.yaw_threshold_deg)),
                "pitch_min": float(pitch_bounds.get("min", -self.pitch_threshold_deg)),
                "pitch_max": float(pitch_bounds.get("max", self.pitch_threshold_deg)),
                "roll_threshold_deg": float(roll_threshold if roll_threshold is not None else self.roll_threshold_deg),
            }

        payload = {
            "version": 2,
            "center_offsets": self.center_offsets,
            "yaw_bounds": {
                "min": self.calibrated_bounds["yaw_min"] if self.calibrated_bounds else -self.yaw_threshold_deg,
                "max": self.calibrated_bounds["yaw_max"] if self.calibrated_bounds else self.yaw_threshold_deg,
            },
            "pitch_bounds": {
                "min": self.calibrated_bounds["pitch_min"] if self.calibrated_bounds else -self.pitch_threshold_deg,
                "max": self.calibrated_bounds["pitch_max"] if self.calibrated_bounds else self.pitch_threshold_deg,
            },
            "roll_threshold_deg": (
                self.calibrated_bounds["roll_threshold_deg"] if self.calibrated_bounds else self.roll_threshold_deg
            ),
            "updated_at": int(time.time()),
        }

        try:
            with open(self.calibration_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError:
            pass

    def track_eyes(self, frame):
        """Annotate frame with face-attention status and pose angles."""
        self._frame_counter += 1
        now = time.monotonic()
        # Both conditions must be true: frame-count gate prevents running on back-to-back
        # frames, and the time gate prevents stalling on very low frame-rate feeds.
        due_by_frame = self._frame_counter % self.frame_skip == 0
        due_by_time = (now - self._last_detection_ts) >= self.detection_interval_seconds

        if due_by_frame and due_by_time:
            rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            result = self.detector.detect(mp_image)
            self.landmarks = result.face_landmarks[0] if result.face_landmarks else None
            self._cached_data = self.extract_eye_data(self.landmarks, frame)
            self._last_detection_ts = now

            if self.draw_pose_axes and self.landmarks is not None:
                self.draw_head_pose(frame, self.landmarks)

        data = self._cached_data

        # Keep this tracker overlay neutral so camera.py is the single source
        # of truth for ATTENTIVE / LOOK_AWAY / LEFT_DESK attention messaging.
        face_status = "YES" if data["face_present"] else "NO"
        face_color = (0, 220, 0) if data["face_present"] else (0, 165, 255)
        cv.putText(frame, f"Face Present: {face_status}", (30, 40), cv.FONT_HERSHEY_SIMPLEX, 0.9, face_color, 2)
        cv.putText(
            frame,
            f"Yaw:{data['yaw_deg']:.1f}  Pitch:{data['pitch_deg']:.1f}  Roll:{data['roll_deg']:.1f}",
            (30, 75),
            cv.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
        cv.putText(
            frame,
            f"Tracking rate cap: {int(1 / self.detection_interval_seconds)} Hz",
            (30, 105),
            cv.FONT_HERSHEY_SIMPLEX,
            0.55,
            (180, 180, 180),
            1,
        )
        return frame

    def extract_eye_data(self, landmarks, frame):
        """Return attention-focused data while keeping previous keys for compatibility."""
        data = {
            "face_present": landmarks is not None,
            "eyes_detected": landmarks is not None,  # Kept for backwards compatibility.
            "left_iris": None,
            "right_iris": None,
            "gaze_state_horizontal": "unknown",
            "gaze_state_vertical": "unknown",
            "yaw_deg": 0.0,
            "pitch_deg": 0.0,
            "roll_deg": 0.0,
            "raw_yaw_deg": 0.0,
            "raw_pitch_deg": 0.0,
            "raw_roll_deg": 0.0,
            "face_facing_screen": False,
            "attention_state": "no_face",
        }

        if landmarks is None:
            return data

        pitch, yaw, roll, _, _, _, _ = self.estimate_head_pose(landmarks, frame)

        data["raw_yaw_deg"] = yaw
        data["raw_pitch_deg"] = pitch
        data["raw_roll_deg"] = roll

        # Offset-corrected values align "center" with the calibrated screen center.
        yaw = yaw - self.center_offsets["yaw_deg"]
        pitch = pitch - self.center_offsets["pitch_deg"]
        roll = roll - self.center_offsets["roll_deg"]

        data["yaw_deg"] = yaw
        data["pitch_deg"] = pitch
        data["roll_deg"] = roll

        # Direction labels retained to avoid breaking older consumers.
        # ±8° yaw and ±7° pitch dead-zones prevent rapid label flicker when the
        # user's gaze is hovering near the center boundary.
        if yaw < -8:
            data["gaze_state_horizontal"] = "left"
        elif yaw > 8:
            data["gaze_state_horizontal"] = "right"
        else:
            data["gaze_state_horizontal"] = "center"

        if pitch < -7:
            data["gaze_state_vertical"] = "up"
        elif pitch > 7:
            data["gaze_state_vertical"] = "down"
        else:
            data["gaze_state_vertical"] = "center"

        if self.calibrated_bounds is not None:
            # Use asymmetric user-specific bounds recorded during corner calibration.
            # These allow for postures where the user naturally sits off-center.
            facing = (
                self.calibrated_bounds["yaw_min"] <= yaw <= self.calibrated_bounds["yaw_max"]
                and self.calibrated_bounds["pitch_min"] <= pitch <= self.calibrated_bounds["pitch_max"]
                and abs(roll) <= self.calibrated_bounds["roll_threshold_deg"]
            )
        else:
            # Symmetric fallback thresholds used when no calibration profile exists.
            facing = (
                abs(yaw) <= self.yaw_threshold_deg
                and abs(pitch) <= self.pitch_threshold_deg
                and abs(roll) <= self.roll_threshold_deg
            )
        data["face_facing_screen"] = facing
        data["attention_state"] = "attentive" if facing else "away"
        return data

    def estimate_head_pose(self, landmarks, frame):
        """Estimate pitch/yaw/roll from a sparse set of facial landmarks."""
        h, w = frame.shape[:2]

        # Six facial landmark indices chosen to span the face robustly:
        # nose tip (1), chin (152), left/right eye corners (33, 263),
        # left/right mouth corners (61, 291).  Multiplying by frame dimensions
        # converts MediaPipe's normalised [0, 1] coordinates into pixel coords.
        image_points = np.array(
            [
                (landmarks[1].x * w, landmarks[1].y * h),    # Nose tip
                (landmarks[152].x * w, landmarks[152].y * h), # Chin
                (landmarks[33].x * w, landmarks[33].y * h),   # Left eye outer corner
                (landmarks[263].x * w, landmarks[263].y * h), # Right eye outer corner
                (landmarks[61].x * w, landmarks[61].y * h),   # Left mouth corner
                (landmarks[291].x * w, landmarks[291].y * h), # Right mouth corner
            ],
            dtype="double",
        )

        # Generic 3-D face model in millimetres (approximate adult average).
        # These are the real-world positions that correspond to the six landmarks
        # above; solvePnP minimises reprojection error between them and image_points.
        model_points = np.array(
            [
                (0.0, 0.0, 0.0),        # Nose tip — origin of the model coordinate system
                (0.0, -63.6, -12.5),    # Chin
                (-43.3, 32.7, -26),     # Left eye outer corner
                (43.3, 32.7, -26),      # Right eye outer corner
                (-28.9, -28.9, -24),    # Left mouth corner
                (28.9, -28.9, -24),     # Right mouth corner
            ],
            dtype="double",
        )

        # Approximate camera intrinsics: focal length = frame width is a common
        # heuristic for webcams without a calibration file (assumes ~60° horizontal FOV).
        focal_length = w
        center = (w / 2, h / 2)  # Principal point assumed at the image centre.
        camera_matrix = np.array(
            [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype="double"
        )
        dist_coeffs = np.zeros((4, 1))  # Assume no lens distortion; good enough for webcams.

        success, rotation_vector, translation_vector = cv.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs
        )
        if not success:
            zero = np.zeros((3, 1), dtype="double")
            return 0.0, 0.0, 0.0, zero, zero, camera_matrix, dist_coeffs

        # Convert the compact axis-angle rotation vector into a full 3×3 rotation matrix.
        rotation_matrix, _ = cv.Rodrigues(rotation_vector)
        # Build the 3×4 projection matrix [R | t] so decomposeProjectionMatrix can
        # extract Euler angles without requiring a separate decomposition library.
        pose_matrix = cv.hconcat((rotation_matrix, translation_vector))
        _, _, _, _, _, _, euler_angles = cv.decomposeProjectionMatrix(pose_matrix)

        pitch = float(euler_angles[0][0])
        yaw = float(euler_angles[1][0])
        roll = float(euler_angles[2][0])

        # decomposeProjectionMatrix outputs angles in [0, 360); remap to [-180, 180]
        # so threshold comparisons like abs(yaw) <= 18 work correctly near 0°.
        pitch = (pitch + 180) % 360 - 180
        yaw = (yaw + 180) % 360 - 180
        roll = (roll + 180) % 360 - 180
        return pitch, yaw, roll, rotation_vector, translation_vector, camera_matrix, dist_coeffs

    def draw_head_pose(self, frame, landmarks):
        """Draw 3D axes to visualize head orientation for debugging."""
        pitch, yaw, roll, rotation_vector, translation_vector, camera_matrix, dist_coeffs = self.estimate_head_pose(
            landmarks, frame
        )
        _ = (pitch, yaw, roll)  # Explicitly keep angle computation; helpful while debugging thresholds.

        h, w = frame.shape[:2]
        nose = (int(landmarks[1].x * w), int(landmarks[1].y * h))

        # Project three 100 mm unit vectors (X, Y, Z) into image space so we can
        # draw them as colour-coded lines anchored at the nose tip.
        axis = np.float32([[100, 0, 0], [0, 100, 0], [0, 0, 100]])
        imgpts, _ = cv.projectPoints(axis, rotation_vector, translation_vector, camera_matrix, dist_coeffs)

        x_axis = tuple(imgpts[0].ravel().astype(int))
        y_axis = tuple(imgpts[1].ravel().astype(int))
        z_axis = tuple(imgpts[2].ravel().astype(int))

        # BGR colour convention: red = X (yaw), green = Y (pitch), blue = Z (roll/depth).
        cv.line(frame, nose, x_axis, (0, 0, 255), 3)
        cv.line(frame, nose, y_axis, (0, 255, 0), 3)
        cv.line(frame, nose, z_axis, (255, 0, 0), 3)