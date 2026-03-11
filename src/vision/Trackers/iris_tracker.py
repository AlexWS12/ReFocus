# iris_tracker.py
# Eye tracking using MediaPipe Face Mesh + Iris

import cv2 as cv
import mediapipe as mp
import os

from mediapipe.tasks.python import vision
from mediapipe.tasks.python import BaseOptions


class eyeTracker:
    """Detects iris landmarks using MediaPipe Face Landmarker."""

    def __init__(self):
        """Load MediaPipe Face Landmarker model."""

        model_path = os.path.join(
            os.path.dirname(__file__),
            "face_landmarker.task"
        )

        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1
        )

        # ✅ Create detector
        self.detector = vision.FaceLandmarker.create_from_options(options)

        # ✅ Store landmarks internally to avoid AttributeErrors
        self.landmarks = None

    def track_eyes(self, frame):
        """Detect iris landmarks and draw them on the frame."""

        # Convert BGR → RGB
        rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = self.detector.detect(mp_image)

        # ✅ Always reset before detection
        self.landmarks = None

        if result.face_landmarks:
            # ✅ Store landmarks internally
            self.landmarks = result.face_landmarks[0]

            h, w, _ = frame.shape

            left_iris = [474, 475, 476, 477]
            right_iris = [469, 470, 471, 472]

            # ✅ Draw iris points using self.landmarks
            for idx in left_iris + right_iris:
                lm = self.landmarks[idx]
                x = int(lm.x * w)
                y = int(lm.y * h)
                cv.circle(frame, (x, y), 2, (0, 255, 0), -1)

        return frame  # ✅ Only return frame; landmarks stored in self.landmarks

    def extract_eye_data(self, landmarks, frame):
        """
        Extract structured data from landmarks.
        Returns a dictionary with iris positions, gaze state, and attention confidence.
        """
        data = {
            "face_present": landmarks is not None,
            "eyes_detected": False,
            "left_iris": None,
            "right_iris": None,
            "gaze_state_horizontal": None,
            "gaze_state_vertical": None,
            "attention_confidence": None
        }

        if landmarks is None:
            return data  # no face detected

        w, h = frame.shape[1], frame.shape[0]

        # --- Iris landmarks in pixels ---
        right_iris = landmarks[468]
        left_iris = landmarks[473]

        rx, ry = int(right_iris.x * w), int(right_iris.y * h)
        lx, ly = int(left_iris.x * w), int(left_iris.y * h)

        data["eyes_detected"] = True
        data["right_iris"] = (rx, ry)
        data["left_iris"] = (lx, ly)

        # --- Horizontal gaze calculation ---
        right_eye_left = int(landmarks[33].x * w)
        right_eye_right = int(landmarks[133].x * w)
        left_eye_left = int(landmarks[362].x * w)
        left_eye_right = int(landmarks[263].x * w)

        right_ratio = (rx - right_eye_left) / (right_eye_right - right_eye_left)
        left_ratio = (lx - left_eye_left) / (left_eye_right - left_eye_left)
        avg_ratio_h = (right_ratio + left_ratio) / 2

        if avg_ratio_h < 0.40:
            data["gaze_state_horizontal"] = "left"
        elif avg_ratio_h > 0.60:
            data["gaze_state_horizontal"] = "right"
        else:
            data["gaze_state_horizontal"] = "center"

        # --- Vertical gaze calculation ---
        r_top = int(landmarks[159].y * h)
        r_bottom = int(landmarks[145].y * h)
        l_top = int(landmarks[386].y * h)
        l_bottom = int(landmarks[374].y * h)

        # Compute denominators safely
        denominator_r = r_bottom - r_top
        denominator_l = l_bottom - l_top

        if denominator_r == 0 or denominator_l == 0:
            avg_ratio_v = 0.5  # default to center if eye is closed
        else:
            right_vert = (ry - r_top) / denominator_r
            left_vert = (ly - l_top) / denominator_l
            avg_ratio_v = (right_vert + left_vert) / 2

        # Clamp ratio to [0, 1]
        avg_ratio_v = max(0.0, min(1.0, avg_ratio_v))

        # Map ratio to gaze direction
        if avg_ratio_v < 0.33: #The 0.33 and 0.66 need to be tweaked to get the correct return values.
            data["gaze_state_vertical"] = "up"
        elif avg_ratio_v > 0.66:
            data["gaze_state_vertical"] = "down"
        else:
            data["gaze_state_vertical"] = "center"
        
        return data