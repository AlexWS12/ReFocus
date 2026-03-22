# camera.py
# Main vision module that combines phone detection (YOLO) and eye tracking.

from ultralytics import YOLO
import cv2 as cv
import numpy as np
import os
import sys
import time
from Trackers.attention_tracker import gazeTracker
from detectors.phone_calibration import PhoneCalibration

# Import DistractionType from the sibling intelligence package.
# Resolves via __file__ so it works whether camera is run directly (src/vision on path)
# or imported from the project root (src on path).
_intel_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "intelligence"))
if _intel_dir not in sys.path:
    sys.path.insert(0, _intel_dir)
try:
    from session_manager import DistractionType as _DistractionType
except ImportError:
    _DistractionType = None  # Graceful degradation if intelligence package is unavailable


class Camera:
    """Manages webcam capture, phone detection (YOLO), and eye tracking.

    Designed to run as a lightweight background process.  YOLO is frame-skipped
    so inference only fires every ``yolo_frame_skip`` frames; cached boxes are
    reused in between via ByteTrack continuity.
    """

    def __init__(self, model_path="yolo26n.pt", session_manager=None):
        """Initialise camera, YOLO model, and eye tracker.

        Args:
            session_manager: Optional SessionManager instance. When provided,
                resolved phone and look-away events are logged via log_distraction().
        """
        self.model = YOLO(model_path)
        self.cap = cv.VideoCapture(0)  # Open default webcam (index 0)
        self.eye_tracker = gazeTracker()
        self.detection_params = {"conf": 0.35}  # Default detection confidence; overwritten after calibration
        self.few_shot_signatures = []            # Appearance exemplars saved during phone calibration
        self.few_shot_similarity_threshold = 0.30  # Min cosine similarity to accept a detection as a phone
        self.few_shot_bundle_path = PhoneCalibration.get_few_shot_bundle_path()
        self.calibrated = False  # True after a successful phone calibration run

        # Frame-skip controls: YOLO only runs every Nth frame.
        # ByteTrack maintains bounding-box continuity on skipped frames, so
        # detections stay smooth without paying inference cost every frame.
        self.yolo_frame_skip = 3       # Run YOLO on frame 0, 3, 6, … (tune up for speed, down for accuracy)
        self._yolo_frame_counter = 0   # Counts total frames seen; used to decide when to re-run YOLO
        self._last_yolo_results = None # Cached result list reused on skipped frames

        # Distraction tracking: each event is defined by a start time and a
        # "last seen" time.  When the trigger disappears, a cooldown window
        # keeps the event open so brief flickers don't split one distraction
        # into many.  Duration is measured start → last_seen (not start → now).
        self._session_manager = session_manager
        self._DISTRACTION_COOLDOWN = 5.0  # seconds of absence before an event is finalized and logged
        self._phone_distraction_start: float | None = None  # wall-clock time the current phone event opened
        self._phone_last_seen: float | None = None          # last frame where a phone was accepted; cooldown ticks from here
        self._look_away_distraction_start: float | None = None  # wall-clock time the current look-away event opened
        self._look_away_last_seen: float | None = None          # last frame where user was looking away
        self._left_desk_distraction_start: float | None = None  # wall-clock time when face first disappeared (user left desk)
        self._left_desk_last_seen: float | None = None          # last frame with no face detected; cooldown ticks from here

        self._load_few_shot_bundle()

    # ------------------------------------------------------------------
    # Bundle / calibration helpers
    # ------------------------------------------------------------------

    def _load_few_shot_bundle(self):
        """Load persisted few-shot signatures and thresholds from the last calibration run."""
        if not os.path.exists(self.few_shot_bundle_path):
            # No calibration file yet — disable few-shot filtering and fall back to YOLO-only detection
            self.detection_params["few_shot_enabled"] = False
            return

        try:
            bundle = np.load(self.few_shot_bundle_path, allow_pickle=False)

            # Each row in "signatures" is a 257-d descriptor (256 HS-histogram bins + 1 edge-density feature)
            signatures = (
                bundle["signatures"]
                if "signatures" in bundle.files
                else np.empty((0, 257), dtype=np.float32)
            )
            self.few_shot_signatures = [
                np.asarray(sig, dtype=np.float32) for sig in signatures
            ]

            # Global cosine similarity threshold chosen during calibration
            self.few_shot_similarity_threshold = (
                float(bundle["threshold_global"])
                if "threshold_global" in bundle.files
                else 0.30
            )

            # Mirror the confidence level the calibrator found optimal so runtime matches calibration behavior
            if "conf_threshold" in bundle.files:
                self.detection_params["conf"] = float(bundle["conf_threshold"])

            # Require at least 3 exemplars before enabling few-shot filtering (fewer = unreliable threshold)
            self.detection_params["few_shot_enabled"] = (
                len(self.few_shot_signatures) >= 3
            )
            self.detection_params["few_shot_similarity_threshold"] = (
                self.few_shot_similarity_threshold
            )
            self.calibrated = True
        except (OSError, ValueError, KeyError):
            # Corrupt or incompatible bundle — degrade gracefully to plain YOLO
            self.few_shot_signatures = []
            self.detection_params["few_shot_enabled"] = False
            self.calibrated = False

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _get_guide_box(self, frame_shape):
        """Use the same centered phone guide-box dimensions as calibration."""
        height, width = frame_shape[:2]
        # 22.4% wide × 47% tall keeps the guide box phone-sized across common resolutions
        box_width = int(width * 0.224)
        box_height = int(height * 0.47)
        x1 = (width - box_width) // 2
        y1 = (height - box_height) // 2
        x2 = x1 + box_width
        y2 = y1 + box_height
        return x1, y1, x2, y2

    # ------------------------------------------------------------------
    # Appearance-matching helpers
    # ------------------------------------------------------------------

    def _extract_crop_from_coords(self, frame, x1, y1, x2, y2, pad_ratio: float = 0.12):
        """Crop and pad around raw pixel coordinates for few-shot matching."""
        h, w = frame.shape[:2]
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        # Add padding proportional to the box size so the descriptor captures context around edges
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

        # 16×16 Hue-Saturation histogram (256 bins) captures color appearance
        hsv = cv.cvtColor(resized, cv.COLOR_BGR2HSV)
        hist_hs = (
            cv.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            .flatten()
            .astype(np.float32)
        )
        hist_hs /= float(hist_hs.sum()) + 1e-6  # L1-normalize so brightness doesn't dominate

        # Single edge-density feature distinguishes phones (hard rectangular edges) from other objects
        gray = cv.cvtColor(resized, cv.COLOR_BGR2GRAY)
        edges = cv.Canny(gray, 80, 160)
        edge_ratio = np.array(
            [float(np.count_nonzero(edges)) / edges.size], dtype=np.float32
        )

        # Concatenate into a 257-d descriptor then L2-normalize for cosine similarity
        sig = np.concatenate([hist_hs, edge_ratio], axis=0)
        norm = float(np.linalg.norm(sig))
        if norm < 1e-8:
            return None
        return sig / norm

    def _few_shot_similarity(self, signature) -> float:
        """Return max cosine similarity against persisted few-shot exemplars."""
        if signature is None or not self.few_shot_signatures:
            return 0.0
        # Take the highest similarity across all exemplars (nearest-neighbor style)
        sims = [float(np.dot(signature, ex)) for ex in self.few_shot_signatures]
        return max(sims) if sims else 0.0

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Main detection loop
    # ------------------------------------------------------------------

    def read_frame(self):
        """Capture a frame, run phone detection and eye tracking.

        Returns:
            tuple: (original_frame, annotated_frame) or None if capture fails.

        Detection pipeline
        ------------------
        1. YOLO inference — every ``yolo_frame_skip`` frames; cached boxes reused in between.
        2. Spatial filter — guide-box gate when uncalibrated.
        3. Appearance filter — few-shot cosine-similarity gate when calibrated.
        4. Best-confidence selection.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        h = frame.shape[0]
        annotated = frame.copy()

        # Draw the guide box when uncalibrated so the user knows where to place their phone
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

        # --- YOLO detection (frame-skipped) ---
        # stream=True yields results lazily, reducing peak memory allocation.
        # On skipped frames the cached result is reused; ByteTrack maintains continuity.
        yolo_conf = self.detection_params.get("conf", 0.35)
        if self._yolo_frame_counter % self.yolo_frame_skip == 0 or self._last_yolo_results is None:
            self._last_yolo_results = list(
                self.model(
                    frame,
                    classes=[67],  # COCO class 67 = cell phone
                    conf=yolo_conf,
                    iou=0.3,
                    imgsz=416,  # Small input size for speed; phones are usually large enough to still be detectable
                    stream=True,  # Lazy generator — reduces peak memory vs returning a list directly
                )
            )
        self._yolo_frame_counter += 1

        # --- Spatial + appearance filtering; pick best candidate ---
        best_coords = None
        best_conf = -1.0
        best_similarity = 0.0
        fallback_coords = None
        fallback_conf = -1.0

        for box in self._last_yolo_results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Before calibration, ignore detections whose center falls outside the guide box
            if not self.calibrated:
                if not (
                    guide_x1 <= center_x <= guide_x2
                    and guide_y1 <= center_y <= guide_y2
                ):
                    continue

            conf = float(box.conf[0])

            # Few-shot appearance filter: reject detections that don't look like the calibrated phone
            similarity = 1.0
            rejected = False
            if self.detection_params.get("few_shot_enabled", False):
                crop = self._extract_crop_from_coords(frame, x1, y1, x2, y2)
                sig = self._compute_few_shot_signature(crop)
                similarity = self._few_shot_similarity(sig)
                print(f"YOLO conf: {conf:.3f}, Similarity: {similarity:.3f}, Threshold: {self.few_shot_similarity_threshold:.3f}")
                if similarity < self.few_shot_similarity_threshold:
                    print("Rejected due to low similarity")
                    # Keep track of high-confidence fallback
                    if conf > 0.5 and conf > fallback_conf:  # High confidence fallback
                        fallback_conf = conf
                        fallback_coords = (x1, y1, x2, y2)
                    rejected = True

            if rejected:
                continue

            # Keep only the highest-confidence box that passed all filters
            if conf > best_conf:
                best_conf = conf
                best_coords = (x1, y1, x2, y2)
                best_similarity = similarity

        # Fallback: if no good match but high-confidence detection available, use it
        if best_coords is None and fallback_coords is not None:
            print("Using high-confidence fallback detection")
            best_coords = fallback_coords
            best_conf = fallback_conf
            best_similarity = 0.0  # Indicate it's a fallback

        # --- Annotate ---
        if best_coords is not None:
            x1, y1, x2, y2 = best_coords
            cv.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv.putText(
                annotated,
                f"PHONE {best_conf:.0%}  sim:{best_similarity:.2f}",
                (x1, y1 - 10),
                cv.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
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

        # --- Eye / gaze tracking ---
        # gazeTracker internally throttles to ~5 Hz; on skipped frames it returns the cached overlay
        annotated = self.eye_tracker.track_eyes(annotated)

        # --- Distraction event logging ---
        self._update_distraction_tracking(best_coords is not None)

        return frame, annotated

    def _update_distraction_tracking(self, phone_detected: bool) -> None:
        """Track distraction events with cooldown merging and priority suppression.

        Cooldown: when a trigger disappears, the event stays open for
        ``_DISTRACTION_COOLDOWN`` seconds.  If the trigger reappears inside
        that window, the event continues seamlessly.  Duration is measured
        from start to last-seen (not start to cooldown-expiry).

        Priority: phone distraction outranks look-away.  While a phone event
        is active (including its cooldown window), look-away tracking is
        suppressed so the same time is not double-counted.
        """
        if self._session_manager is None or _DistractionType is None:
            return

        now = time.time()
        attention_data = self.eye_tracker._cached_data
        face_present = attention_data.get("face_present", True)
        # Separate left-desk (no face in frame) from look-away (face present but not facing screen).
        # Previously both resolved to looking_away=True because face_facing_screen is False in both
        # cases, causing absent-user time to be logged under the wrong distraction type.
        looking_away = face_present and not attention_data.get("face_facing_screen", True)
        left_desk = not face_present  # True when MediaPipe detects no face at all

        # --- Phone distraction (highest priority) ---
        if phone_detected:
            if self._phone_distraction_start is None:
                self._phone_distraction_start = now  # open a new event on first detection
            self._phone_last_seen = now  # keep refreshing so the cooldown resets each frame
        elif self._phone_distraction_start is not None:
            # Phone is gone but the event is still open — wait out the cooldown before logging.
            # This merges flickers (phone briefly leaves then returns) into a single event.
            if now - self._phone_last_seen >= self._DISTRACTION_COOLDOWN:
                # Cooldown expired: duration is start → last_seen, NOT start → now,
                # so the 5s wait doesn't inflate the reported distraction length.
                duration = max(1, int(self._phone_last_seen - self._phone_distraction_start))
                try:
                    self._session_manager.log_distraction(_DistractionType.PHONE_DISTRACTION, duration)
                except Exception:
                    pass  # Session may not be IN_PROGRESS; never crash the camera loop
                self._phone_distraction_start = None
                self._phone_last_seen = None

        # --- Look-away distraction (suppressed while phone event is active) ---
        # A phone event includes its cooldown window: even if the phone just left the
        # frame, we don't start counting a new look-away until the phone event fully closes.
        phone_active = self._phone_distraction_start is not None
        if phone_active:
            # Phone takes priority — drop any in-progress look-away or left-desk so the same
            # distraction window isn't counted twice under two different types.
            if self._look_away_distraction_start is not None:
                self._look_away_distraction_start = None
                self._look_away_last_seen = None
            if self._left_desk_distraction_start is not None:  # clear left-desk too; phone wins
                self._left_desk_distraction_start = None
                self._left_desk_last_seen = None
            return

        # --- Left-desk distraction (face absent; user physically left desk) ---
        if left_desk:
            # If a look-away was open, discard it — user left the desk so the look-away
            # is superseded by the more significant absence event.
            if self._look_away_distraction_start is not None:
                self._look_away_distraction_start = None
                self._look_away_last_seen = None
            if self._left_desk_distraction_start is None:
                self._left_desk_distraction_start = now  # open event the first frame face is gone
            self._left_desk_last_seen = now  # refresh every frame face stays absent so cooldown resets
        else:
            # Face reappeared — the user is back; check if open left-desk event has cooled down.
            if self._left_desk_distraction_start is not None:
                if now - self._left_desk_last_seen >= self._DISTRACTION_COOLDOWN:
                    # Same start→last_seen duration rule: don't count the cooldown wait as desk-leave time
                    duration = max(1, int(self._left_desk_last_seen - self._left_desk_distraction_start))
                    try:
                        self._session_manager.log_distraction(_DistractionType.LEFT_DESK_DISTRACTION, duration)
                    except Exception:
                        pass  # Session may not be IN_PROGRESS; never crash the camera loop
                    self._left_desk_distraction_start = None
                    self._left_desk_last_seen = None

            # --- Look-away (only evaluated when face is present; left-desk takes priority above) ---
            if looking_away:
                if self._look_away_distraction_start is None:
                    self._look_away_distraction_start = now  # open a new look-away event
                self._look_away_last_seen = now  # refresh so brief returns to screen don't close the event
            elif self._look_away_distraction_start is not None:
                # User is back on screen — wait out the cooldown before finalizing,
                # same rationale as phone: prevents brief glances from splitting events.
                if now - self._look_away_last_seen >= self._DISTRACTION_COOLDOWN:
                    duration = max(1, int(self._look_away_last_seen - self._look_away_distraction_start))
                    try:
                        self._session_manager.log_distraction(_DistractionType.LOOK_AWAY_DISTRACTION, duration)
                    except Exception:
                        pass
                    self._look_away_distraction_start = None
                    self._look_away_last_seen = None

    def release(self):
        """Release camera resources and close windows.

        Flushes any open distraction events so they are not silently lost.
        """
        self._flush_open_distractions()
        self.cap.release()
        cv.destroyAllWindows()

    def _flush_open_distractions(self) -> None:
        """Log any in-progress distraction events before the camera shuts down.

        Uses last_seen (not now) so duration reflects actual distraction time,
        not time spent waiting for the cooldown to expire.
        """
        if self._session_manager is None or _DistractionType is None:
            return

        if self._phone_distraction_start is not None:
            # Use last_seen as the end boundary — the camera is shutting down, not
            # the phone disappearing, so we don't want to pad with cooldown time.
            end = self._phone_last_seen or time.time()
            duration = max(1, int(end - self._phone_distraction_start))
            try:
                self._session_manager.log_distraction(_DistractionType.PHONE_DISTRACTION, duration)
            except Exception:
                pass
            self._phone_distraction_start = None
            self._phone_last_seen = None

        if self._look_away_distraction_start is not None:
            end = self._look_away_last_seen or time.time()  # same rationale as phone flush above
            duration = max(1, int(end - self._look_away_distraction_start))
            try:
                self._session_manager.log_distraction(_DistractionType.LOOK_AWAY_DISTRACTION, duration)
            except Exception:
                pass
            self._look_away_distraction_start = None
            self._look_away_last_seen = None

        if self._left_desk_distraction_start is not None:
            end = self._left_desk_last_seen or time.time()  # same rationale as phone flush above
            duration = max(1, int(end - self._left_desk_distraction_start))
            try:
                self._session_manager.log_distraction(_DistractionType.LEFT_DESK_DISTRACTION, duration)
            except Exception:
                pass
            self._left_desk_distraction_start = None
            self._left_desk_last_seen = None


# Runs only when camera.py is executed directly
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
