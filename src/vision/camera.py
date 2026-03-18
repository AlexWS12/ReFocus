# camera.py
# Main vision module combining phone detection (YOLO + Grounding DINO) and eye tracking.

from ultralytics import YOLO
import cv2 as cv
import numpy as np
import os
from Trackers.attention_tracker import gazeTracker
from phone_calibration import PhoneCalibration
from dino_detector import DinoDetector


class Camera:
    """Manages webcam capture, phone detection (YOLO + Grounding DINO), and eye tracking.

    Detection strategy
    ------------------
    YOLO runs on every frame (fast, ~10–30 ms).  Grounding DINO is used as a
    supplemental detector: it runs every ``_DINO_RUN_INTERVAL`` frames *and*
    immediately whenever YOLO produces zero candidates.  Results from both
    models are merged with IoU-based deduplication so the same phone is never
    double-counted.  DINO detections are shown in a distinct orange colour to
    make the source easy to spot during debugging.
    """

    _DINO_RUN_INTERVAL = 5  # run DINO at least once every N frames for freshness

    def __init__(self, model_path="yolo26n.pt"):
        """Initialise camera, YOLO, Grounding DINO, and eye tracker."""
        self.model = YOLO(model_path)
        self.cap = cv.VideoCapture(0)
        self.eye_tracker = gazeTracker()
        self.detection_params = {"conf": 0.35}
        self.few_shot_signatures = []
        self.few_shot_similarity_threshold = 0.45
        self.few_shot_bundle_path = PhoneCalibration.get_few_shot_bundle_path()
        self.calibrated = False

        # Grounding DINO — lazy-loads weights on first use
        self.dino = DinoDetector()
        self._dino_frame_count = 0
        self._dino_last_run_frame = -self._DINO_RUN_INTERVAL  # force early run
        self._dino_last_detections: list = []  # cached (x1,y1,x2,y2,score) tuples

        self._load_few_shot_bundle()

    # ------------------------------------------------------------------
    # Bundle / calibration helpers
    # ------------------------------------------------------------------

    def _load_few_shot_bundle(self):
        """Load persisted few-shot signatures and thresholds from the last calibration run."""
        if not os.path.exists(self.few_shot_bundle_path):
            self.detection_params["few_shot_enabled"] = False
            return

        try:
            bundle = np.load(self.few_shot_bundle_path, allow_pickle=False)
            signatures = (
                bundle["signatures"]
                if "signatures" in bundle.files
                else np.empty((0, 257), dtype=np.float32)
            )
            self.few_shot_signatures = [
                np.asarray(sig, dtype=np.float32) for sig in signatures
            ]
            self.few_shot_similarity_threshold = (
                float(bundle["threshold_global"])
                if "threshold_global" in bundle.files
                else 0.45
            )
            if "conf_threshold" in bundle.files:
                self.detection_params["conf"] = float(bundle["conf_threshold"])
            self.detection_params["few_shot_enabled"] = (
                len(self.few_shot_signatures) >= 3
            )
            self.detection_params["few_shot_similarity_threshold"] = (
                self.few_shot_similarity_threshold
            )
            self.calibrated = True
        except (OSError, ValueError, KeyError):
            self.few_shot_signatures = []
            self.detection_params["few_shot_enabled"] = False
            self.calibrated = False

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

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

    @staticmethod
    def _iou(a, b) -> float:
        """Intersection-over-Union for two (x1, y1, x2, y2) boxes."""
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
        return inter / max(1, union)

    # ------------------------------------------------------------------
    # Appearance-matching helpers
    # ------------------------------------------------------------------

    def _extract_crop_from_coords(
        self, frame, x1, y1, x2, y2, pad_ratio: float = 0.12
    ):
        """Crop and pad around raw pixel coordinates for few-shot matching."""
        h, w = frame.shape[:2]
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
        hist_hs = (
            cv.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            .flatten()
            .astype(np.float32)
        )
        hist_hs /= float(hist_hs.sum()) + 1e-6

        gray = cv.cvtColor(resized, cv.COLOR_BGR2GRAY)
        edges = cv.Canny(gray, 80, 160)
        edge_ratio = np.array(
            [float(np.count_nonzero(edges)) / edges.size], dtype=np.float32
        )

        sig = np.concatenate([hist_hs, edge_ratio], axis=0)
        norm = float(np.linalg.norm(sig))
        if norm < 1e-8:
            return None
        return sig / norm

    def _few_shot_similarity(self, signature) -> float:
        """Return max cosine similarity against persisted few-shot exemplars."""
        if signature is None or not self.few_shot_signatures:
            return 0.0
        sims = [float(np.dot(signature, ex)) for ex in self.few_shot_signatures]
        return max(sims) if sims else 0.0

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self) -> bool:
        """Run interactive calibration before starting detection."""
        calibrator = PhoneCalibration()
        result = calibrator.run_calibration()

        if result.get("success"):
            self.detection_params = calibrator.get_optimal_params()
            self.calibrated = True
            print(f"Using params: {self.detection_params}")
            return True
        else:
            self.calibrated = False
            print(f"Calibration failed: {result.get('message')}")
            return False

    # ------------------------------------------------------------------
    # Main detection loop
    # ------------------------------------------------------------------

    def read_frame(self):
        """Capture a frame, run phone detection (YOLO + DINO) and eye tracking.

        Returns:
            tuple: (original_frame, annotated_frame) or None if capture fails.

        Detection pipeline
        ------------------
        1. YOLO inference — every frame.
        2. Grounding DINO — every ``_DINO_RUN_INTERVAL`` frames OR immediately
           when YOLO finds nothing.  Results are cached; non-overlapping DINO
           boxes are merged into the candidate pool.
        3. Spatial filter — guide-box gate when uncalibrated.
        4. Appearance filter — few-shot cosine-similarity gate when calibrated.
        5. Best-confidence selection.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        h, w = frame.shape[:2]
        annotated = frame.copy()

        # Guide box (uncalibrated mode only)
        if not self.calibrated:
            guide_x1, guide_y1, guide_x2, guide_y2 = self._get_guide_box(frame.shape)
            cv.rectangle(
                annotated, (guide_x1, guide_y1), (guide_x2, guide_y2), (0, 255, 255), 2
            )
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

        # --- YOLO detection ---
        yolo_conf = self.detection_params.get("conf", 0.35)
        yolo_results = self.model(
            frame, classes=[67], conf=yolo_conf, iou=0.3, imgsz=640
        )
        # Collect as plain tuples: (x1, y1, x2, y2, conf, source)
        candidates: list = []
        for box in yolo_results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            candidates.append((x1, y1, x2, y2, float(box.conf[0]), "yolo"))

        # --- Grounding DINO (supplemental / fallback) ---
        self._dino_frame_count += 1
        frames_since_dino = self._dino_frame_count - self._dino_last_run_frame
        run_dino = (not candidates and frames_since_dino >= 2) or (
            frames_since_dino >= self._DINO_RUN_INTERVAL
        )
        if run_dino and self.dino.available:
            self._dino_last_run_frame = self._dino_frame_count
            # Use a slightly lower threshold so DINO catches borderline cases
            dino_conf = max(0.15, yolo_conf * 0.75)
            self._dino_last_detections = self.dino.detect(
                frame, conf_threshold=dino_conf
            )

        # Merge DINO boxes that don't substantially overlap any YOLO detection
        for dx1, dy1, dx2, dy2, dconf in self._dino_last_detections:
            dbox = (dx1, dy1, dx2, dy2)
            overlaps_yolo = any(
                self._iou(dbox, (cx1, cy1, cx2, cy2)) > 0.3
                for cx1, cy1, cx2, cy2, _, _ in candidates
            )
            if not overlaps_yolo:
                candidates.append((dx1, dy1, dx2, dy2, dconf, "dino"))

        # --- Spatial + appearance filtering; pick best ---
        best_coords = None
        best_conf = -1.0
        best_similarity = 0.0
        best_source = "yolo"

        for x1, y1, x2, y2, conf, source in candidates:
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            if not self.calibrated:
                if not (
                    guide_x1 <= center_x <= guide_x2
                    and guide_y1 <= center_y <= guide_y2
                ):
                    continue

            similarity = 1.0
            if self.detection_params.get("few_shot_enabled", False):
                crop = self._extract_crop_from_coords(frame, x1, y1, x2, y2)
                sig = self._compute_few_shot_signature(crop)
                similarity = self._few_shot_similarity(sig)
                if similarity < self.few_shot_similarity_threshold:
                    continue

            if conf > best_conf:
                best_conf = conf
                best_coords = (x1, y1, x2, y2)
                best_similarity = similarity
                best_source = source

        # --- Annotate ---
        if best_coords is not None:
            x1, y1, x2, y2 = best_coords
            # Green = YOLO confirmed, orange = DINO caught what YOLO missed
            color = (0, 255, 0) if best_source == "yolo" else (0, 200, 255)
            cv.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            cv.putText(
                annotated,
                f"PHONE({best_source.upper()}) {best_conf:.0%}  sim:{best_similarity:.2f}",
                (x1, y1 - 10),
                cv.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2,
            )
        else:
            no_phone_text = (
                "No phone detected"
                if self.calibrated
                else "No valid phone in guide box"
            )
            cv.putText(
                annotated,
                no_phone_text,
                (10, h - 18),
                cv.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 255),
                2,
            )

        # Eye tracking
        annotated = self.eye_tracker.track_eyes(annotated)
        eye_data = self.eye_tracker.extract_eye_data(
            self.eye_tracker.landmarks, annotated
        )

        return frame, annotated

    def release(self):
        """Release camera resources and close windows."""
        self.cap.release()
        cv.destroyAllWindows()


# Runs only when camera.py is executed directly
if __name__ == "__main__":
    cam = Camera()

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
