# camera.py
# Main vision module that combines phone detection and eye tracking.

from ultralytics import YOLO
import cv2 as cv
import numpy as np
import os
from src.vision.Trackers.attention_tracker import gazeTracker
from src.vision.phone_calibration import PhoneCalibration


class Camera:
    """Manages webcam capture, phone detection (YOLO), and eye tracking."""

    def __init__(self, model_path="yolo26n.pt"):
        """Initialize camera, YOLO model, and eye tracker."""
        self.model = YOLO(model_path)  # Load YOLO model for object detection
        self.cap = cv.VideoCapture(0)  # Open default webcam (index 0)
        self.eye_tracker = gazeTracker()
        self.detection_params = {"conf": 0.35}  # Default parameters
        self.few_shot_signatures = []
        self.few_shot_similarity_threshold = 0.45
        self.few_shot_bundle_path = PhoneCalibration.get_few_shot_bundle_path()
        self.calibrated = False  # true after successful calibration
        self._load_few_shot_bundle()

    def _load_few_shot_bundle(self):
        """Load persisted few-shot signatures and thresholds from the last calibration run."""
        if not os.path.exists(self.few_shot_bundle_path):
            self.detection_params["few_shot_enabled"] = False
            return

        try:
            bundle = np.load(self.few_shot_bundle_path, allow_pickle=False)
            signatures = bundle["signatures"] if "signatures" in bundle.files else np.empty((0, 257), dtype=np.float32)
            self.few_shot_signatures = [np.asarray(sig, dtype=np.float32) for sig in signatures]
            self.few_shot_similarity_threshold = float(bundle["threshold_global"]) if "threshold_global" in bundle.files else 0.45

            # Runtime should mirror calibrated detector sensitivity when bundle is present.
            if "conf_threshold" in bundle.files:
                self.detection_params["conf"] = float(bundle["conf_threshold"])

            self.detection_params["few_shot_enabled"] = len(self.few_shot_signatures) >= 3
            self.detection_params["few_shot_similarity_threshold"] = self.few_shot_similarity_threshold
            self.calibrated = True
        except (OSError, ValueError, KeyError):
            self.few_shot_signatures = []
            self.detection_params["few_shot_enabled"] = False
            self.calibrated = False

    def _get_guide_box(self, frame_shape):
        """Use the same centered phone guide-box dimensions as calibration."""
        height, width = frame_shape[:2]
        box_width = int(width * 0.224)
        box_height = int(height * 0.47)
        x1 = (width - box_width) // 2
        y1 = (height - box_height) // 2
        x2 = x1 + box_width
        y2 = y1 + box_height
        return x1, y1, x2, y2

    def _extract_phone_crop(self, frame, box, pad_ratio: float = 0.12):
        """Crop and pad around a YOLO box for appearance-signature matching."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        px = int(bw * pad_ratio)
        py = int(bh * pad_ratio)
        cx1 = max(0, x1 - px)
        cy1 = max(0, y1 - py)
        cx2 = min(w, x2 + px)
        cy2 = min(h, y2 + py)
        if cx2 <= cx1 or cy2 <= cy1:
            return None
        return frame[cy1:cy2, cx1:cx2]

    def _compute_few_shot_signature(self, crop):
        """Match calibration descriptor: normalized HS histogram + edge-density feature."""
        if crop is None or crop.size == 0:
            return None

        resized = cv.resize(crop, (96, 96), interpolation=cv.INTER_AREA)
        hsv = cv.cvtColor(resized, cv.COLOR_BGR2HSV)
        hist_hs = cv.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256]).flatten().astype(np.float32)
        hist_hs /= float(hist_hs.sum()) + 1e-6

        gray = cv.cvtColor(resized, cv.COLOR_BGR2GRAY)
        edges = cv.Canny(gray, 80, 160)
        edge_ratio = np.array([float(np.count_nonzero(edges)) / edges.size], dtype=np.float32)

        sig = np.concatenate([hist_hs, edge_ratio], axis=0)
        norm = float(np.linalg.norm(sig))
        if norm < 1e-8:
            return None
        return sig / norm

    def _few_shot_similarity(self, signature) -> float:
        """Return cosine similarity against persisted few-shot exemplars."""
        if signature is None or not self.few_shot_signatures:
            return 0.0
        sims = [float(np.dot(signature, ex)) for ex in self.few_shot_signatures]
        return max(sims) if sims else 0.0

    def calibrate(self) -> bool:
        """Run interactive calibration before starting detection."""
        calibrator = PhoneCalibration()
        result = calibrator.run_calibration()  # Uses new multi-phase flow
        
        if result.get("success"):
            self.detection_params = calibrator.get_optimal_params()
            self.calibrated = True
            print(f"Using params: {self.detection_params}")
            return True
        else:
            self.calibrated = False
            print(f"Calibration failed: {result.get('message')}")
            return False
        
    def read_frame(self):
        """Capture a frame, run phone detection and eye tracking.
        
        Returns:
            tuple: (original_frame, annotated_frame) or None if capture fails.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        # Detect phones only (class 67 in COCO dataset)
        results = self.model(frame, classes=[67], conf=self.detection_params.get("conf", 0.35), iou=0.3, imgsz=640)
        annotated = frame.copy()

        if not self.calibrated:
            guide_x1, guide_y1, guide_x2, guide_y2 = self._get_guide_box(frame.shape)
            cv.rectangle(annotated, (guide_x1, guide_y1), (guide_x2, guide_y2), (0, 255, 255), 2)
            cv.putText(
                annotated,
                "Phone guide box",
                (guide_x1 - 12, guide_y1 - 10),
                cv.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )
        else:
            guide_x1 = guide_y1 = guide_x2 = guide_y2 = None

        best_valid_box = None
        best_valid_conf = -1.0
        best_similarity = 0.0
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            if not self.calibrated:
                in_box = guide_x1 <= center_x <= guide_x2 and guide_y1 <= center_y <= guide_y2
                if not in_box:
                    continue
            else:
                in_box = True

            similarity = 1.0
            if self.detection_params.get("few_shot_enabled", False):
                crop = self._extract_phone_crop(frame, box)
                sig = self._compute_few_shot_signature(crop)
                similarity = self._few_shot_similarity(sig)
                if similarity < self.few_shot_similarity_threshold:
                    continue

            conf = float(box.conf[0])
            if conf > best_valid_conf:
                best_valid_conf = conf
                best_valid_box = box
                best_similarity = similarity

        if best_valid_box is not None:
            x1, y1, x2, y2 = map(int, best_valid_box.xyxy[0])
            cv.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv.putText(
                annotated,
                f"PHONE {best_valid_conf:.0%}  sim:{best_similarity:.2f}",
                (x1, y1 - 10),
                cv.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
            )
        else:
            if self.calibrated:
                no_phone_text = "No phone detected"
            else:
                no_phone_text = "No valid phone in guide box"
            cv.putText(
                annotated,
                no_phone_text,
                (10, frame.shape[0] - 18),
                cv.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 255),
                2,
            )

        # Track eyes (landmarks stored internally)
        annotated = self.eye_tracker.track_eyes(annotated)

        # Extract eye data from internal landmarks
        eye_data = self.eye_tracker.extract_eye_data(self.eye_tracker.landmarks, annotated)


        return frame, annotated

    def release(self):
        """Release camera resources and close windows."""
        self.cap.release()
        cv.destroyAllWindows()


# This loop only runs if you click "Run" on camera.py
if __name__ == "__main__":
    cam = Camera()
    
    # Run calibration first
    print("Starting calibration...")
    if cam.calibrate():
        print("Calibration successful! Starting detection...")
    else:
        print("Calibration failed. Using default parameters.")
    
    while True:
        data = cam.read_frame()
        if data is None:
            break
        _, annotated = data
        cv.imshow("Phone Detection", annotated)
        if cv.waitKey(1) == ord("q"):
            break
    cam.release()