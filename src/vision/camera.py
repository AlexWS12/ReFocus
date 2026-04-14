# camera.py
# Main vision module that combines phone detection (YOLO) and eye tracking.

import cv2 as cv
import importlib
import numpy as np
import os
import time


_gaze_tracker_cls = None
_phone_calibration_cls = None
_DistractionType = None
_yolo_cls = None


def _import_symbol(primary_module: str, fallback_module: str, symbol: str):
    """Resolve a symbol via project-root package path first, then local path.

    This keeps camera.py importable both as `src.vision.camera` and as `camera`
    without mutating sys.path.
    """
    for module_path in (primary_module, fallback_module):
        try:
            return getattr(importlib.import_module(module_path), symbol)
        except (ModuleNotFoundError, AttributeError):
            continue
    raise ImportError(
        f"Cannot resolve {symbol} from {primary_module} or {fallback_module}"
    )


def _get_gaze_tracker_cls():
    """Return the gaze tracker class, importing it once on first use.

    Lazy loading keeps vision helper modules lightweight when only calibration
    or menu actions are needed.
    """
    global _gaze_tracker_cls
    if _gaze_tracker_cls is None:
        _gaze_tracker_cls = _import_symbol(
            "src.vision.Trackers.attention_tracker",
            "Trackers.attention_tracker",
            "gazeTracker",
        )
    return _gaze_tracker_cls


def _get_phone_calibration_cls():
    """Return the phone calibration class, importing it once on first use."""
    global _phone_calibration_cls
    if _phone_calibration_cls is None:
        _phone_calibration_cls = _import_symbol(
            "src.vision.detectors.phone_calibration",
            "detectors.phone_calibration",
            "PhoneCalibration",
        )
    return _phone_calibration_cls


def _get_yolo_cls():
    """Return the YOLO class, importing ultralytics lazily on first use.

    This keeps module import overhead low for helper-only/test paths that do not
    instantiate the runtime camera pipeline.
    """
    global _yolo_cls
    if _yolo_cls is None:
        _yolo_cls = _import_symbol("ultralytics", "ultralytics", "YOLO")
    return _yolo_cls


def _import_distraction_type():
    """Lazily resolve DistractionType from the sibling intelligence package.

    Tries the project-root path first (src.intelligence.session_manager),
    then the flat module name used when running directly from src/vision.
    Returns None if the intelligence package is unavailable.
    """
    for module_path in ("src.intelligence.session_manager", "session_manager"):
        try:
            return getattr(importlib.import_module(module_path), "DistractionType")
        except (ModuleNotFoundError, AttributeError):
            continue
    return None


def _get_distraction_type():
    """Resolve DistractionType once and cache it for subsequent calls."""
    global _DistractionType
    if _DistractionType is None:
        _DistractionType = _import_distraction_type()
    return _DistractionType


class Camera:
    """Manages webcam capture, phone detection (YOLO), and eye tracking.

    Designed to run as a lightweight background process.  YOLO is frame-skipped
    so inference only fires every ``yolo_frame_skip`` frames; cached boxes are
    reused in between via ByteTrack continuity.
    """

    def __init__(self, model_path="yolo26n.pt", session_manager=None, camera_index: int = 0):
        """Initialise camera, YOLO model, and eye tracker.

        Args:
            session_manager: Optional SessionManager instance. When provided,
                resolved phone and look-away events are logged via log_distraction().
            camera_index: Which video-capture device to open (default 0).
        """
        # YOLO stays in __init__ so heavy model load happens only when camera runtime starts.
        self.model = _get_yolo_cls()(model_path)
        self.cap = cv.VideoCapture(camera_index)
        self.eye_tracker = _get_gaze_tracker_cls()()
        self.detection_params = {}               # Populated exclusively from the calibration bundle
        self.few_shot_signatures = []            # Appearance exemplars saved during phone calibration

        # --- User-tunable detection thresholds ---
        # Set by _load_few_shot_bundle() from the values learned during calibration.
        # Can be adjusted at runtime (e.g. from the frontend) without re-running calibration.
        self.yolo_conf_threshold: float | None = None       # YOLO minimum confidence; None until calibrated
        self.few_shot_similarity_threshold: float | None = None  # Cosine similarity gate; None until calibrated
        self.fallback_conf_threshold: float | None = None   # Accept high-confidence detection even if appearance rejected; None until calibrated

        self.few_shot_bundle_path = _get_phone_calibration_cls().get_few_shot_bundle_path()
        self.calibrated = False  # True after a successful phone calibration run

        # Frame-skip controls: YOLO and MediaPipe both run every Nth frame.
        # ByteTrack maintains bounding-box continuity on skipped frames, so
        # detections stay smooth without paying inference cost every frame.
        self.frame_skip = 3            # Run detectors on frame 0, 3, 6, … (tune up for speed, down for accuracy)
        self._frame_counter = 0        # Counts total frames seen; used to decide when to re-run detectors
        self._last_yolo_results = None # Cached result list reused on skipped frames
        self._last_gaze_annotated = None  # Cached gaze overlay reused on skipped frames

        # FPS cap: sleep at the top of read_frame() to maintain a consistent frame rate.
        self.target_fps = 30
        self._last_frame_time: float = 0.0  # wall-clock time of the previous read_frame() call

        # Distraction tracking: each event is defined by a start time and a
        # "last seen" time.  When the trigger disappears, a cooldown window
        # keeps the event open so brief flickers don't split one distraction
        # into many.  Duration is measured start → last_seen (not start → now).
        self._session_manager = session_manager
        self._on_distraction_started = None  # callback(distraction_type_str) set by VisionManager
        self._DISTRACTION_COOLDOWN = 5.0  # seconds of absence before an event is finalized and logged
        self._LEFT_DESK_TRANSITION_SECONDS = 10.0  # promote no-face look-away to left-desk after continuous absence
        self._phone_distraction_start: float | None = None  # wall-clock time the current phone event opened
        self._phone_last_seen: float | None = None          # last frame where a phone was accepted; cooldown ticks from here
        self._look_away_distraction_start: float | None = None  # wall-clock time the current look-away event opened
        self._look_away_last_seen: float | None = None          # last frame where user was looking away
        self._left_desk_distraction_start: float | None = None  # wall-clock time when face first disappeared (user left desk)
        self._left_desk_last_seen: float | None = None          # last frame with no face detected; cooldown ticks from here
        # Separate timer for the 15s LEFT_DESK promotion.  Must NOT share _look_away_distraction_start
        # because look-away can begin while the face is still present (face turned away); we only want
        # to count continuous *no-face* time toward the promotion threshold.
        self._no_face_since: float | None = None  # wall-clock time the face first disappeared in the current absence

        self._load_few_shot_bundle()
        self._apply_settings_overrides()

    # ------------------------------------------------------------------
    # Bundle / calibration helpers
    # ------------------------------------------------------------------

    def _load_few_shot_bundle(self):
        """Load calibration-derived thresholds and exemplars from the saved bundle.

        Sets yolo_conf_threshold, few_shot_similarity_threshold, and
        fallback_conf_threshold from values computed during calibration.
        All three remain None if the bundle is missing or corrupt, signalling
        that the user must run phone calibration before launching the camera.

        [INTELLIGENCE TEAM] conf_threshold and threshold_global must be present
        in the .npz bundle written by PhoneCalibration._save_few_shot_bundle().
        If either key is missing the camera will refuse to start (calibrated=False).

        [UX/UI TEAM] yolo_conf_threshold, few_shot_similarity_threshold, and
        fallback_conf_threshold are the three values users should be able to
        adjust from the settings panel without re-running calibration. Expose
        them as sliders/inputs and write back to cam.yolo_conf_threshold etc.
        at runtime — no restart needed.
        """
        if not os.path.exists(self.few_shot_bundle_path):
            self.detection_params["few_shot_enabled"] = False
            return

        try:
            bundle = np.load(self.few_shot_bundle_path, allow_pickle=False)

            # Each row is a 257-d descriptor (256 HS-histogram bins + 1 edge-density feature)
            signatures = (
                bundle["signatures"]
                if "signatures" in bundle.files
                else np.empty((0, 257), dtype=np.float32)
            )
            self.few_shot_signatures = [
                np.asarray(sig, dtype=np.float32) for sig in signatures
            ]

            # [INTELLIGENCE TEAM] These three thresholds come exclusively from calibration.
            # No hardcoded fallbacks — if a key is missing the bundle is considered incomplete.
            self.yolo_conf_threshold = (
                float(bundle["conf_threshold"])
                if "conf_threshold" in bundle.files
                else None
            )
            self.few_shot_similarity_threshold = (
                float(bundle["threshold_global"])
                if "threshold_global" in bundle.files
                else None
            )
            # fallback_conf_threshold: accept a detection that appearance-matching rejected
            # when YOLO is this confident. Seeded slightly above yolo_conf_threshold so it
            # only fires on genuinely high-confidence detections the appearance gate may have
            # been too strict about. [UX/UI TEAM] expose as an advanced slider.
            self.fallback_conf_threshold = (
                min(1.0, self.yolo_conf_threshold + 0.15)
                if self.yolo_conf_threshold is not None
                else None
            )

            self.detection_params["conf"] = self.yolo_conf_threshold
            self.detection_params["few_shot_enabled"] = len(self.few_shot_signatures) >= 3
            self.detection_params["few_shot_similarity_threshold"] = self.few_shot_similarity_threshold
            self.calibrated = True
        except (OSError, ValueError, KeyError):
            # Corrupt or incompatible bundle — user must re-run calibration
            self.few_shot_signatures = []
            self.detection_params["few_shot_enabled"] = False
            self.calibrated = False

    def _apply_settings_overrides(self):
        """Apply user-configured detection thresholds from settings.json.

        Runs after _load_few_shot_bundle() so calibration values are loaded
        first, then overridden by any non-None user settings. Also applies
        gaze angle thresholds to the eye_tracker instance.
        """
        try:
            from src.core import settings_manager
            thresholds = settings_manager.detection_thresholds()
        except ImportError:
            return

        if thresholds.get("yolo_conf") is not None:
            self.yolo_conf_threshold = thresholds["yolo_conf"]
            self.detection_params["conf"] = self.yolo_conf_threshold
        if thresholds.get("few_shot_similarity") is not None:
            self.few_shot_similarity_threshold = thresholds["few_shot_similarity"]
            self.detection_params["few_shot_similarity_threshold"] = self.few_shot_similarity_threshold
        if thresholds.get("fallback_conf") is not None:
            self.fallback_conf_threshold = thresholds["fallback_conf"]

        if thresholds.get("yaw_threshold_deg") is not None:
            self.eye_tracker.yaw_threshold_deg = thresholds["yaw_threshold_deg"]
        if thresholds.get("pitch_threshold_deg") is not None:
            self.eye_tracker.pitch_threshold_deg = thresholds["pitch_threshold_deg"]
        if thresholds.get("roll_threshold_deg") is not None:
            self.eye_tracker.roll_threshold_deg = thresholds["roll_threshold_deg"]

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
        calibrator = _get_phone_calibration_cls()()
        result = calibrator.run_calibration()  # Uses new multi-phase flow

        if result.get("success"):
            self.detection_params = calibrator.get_optimal_params()
            # Reload the bundle so all three tunable thresholds are refreshed from
            # the newly saved calibration data.
            self._load_few_shot_bundle()
            return True
        else:
            self.calibrated = False
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
        # Enforce FPS cap: sleep for whatever time remains in the current frame budget.
        now = time.time()
        elapsed = now - self._last_frame_time
        frame_budget = 1.0 / self.target_fps
        if elapsed < frame_budget:
            time.sleep(frame_budget - elapsed)
        self._last_frame_time = time.time()

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

        # --- Detector frame-skip decision ---
        # Both YOLO and MediaPipe run on the same cadence; cached results fill skipped frames.
        run_detectors = self._frame_counter % self.frame_skip == 0 or self._last_yolo_results is None
        self._frame_counter += 1

        # --- YOLO detection (frame-skipped) ---
        # stream=True yields results lazily, reducing peak memory allocation.
        # On skipped frames the cached result is reused; ByteTrack maintains continuity.
        yolo_conf = self.yolo_conf_threshold or self.detection_params.get("conf", 0.35)
        if run_detectors:
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

        # --- Spatial + appearance filtering; pick best candidate ---
        best_coords = None
        best_conf = -1.0
        best_is_fallback = False
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
                if similarity < self.few_shot_similarity_threshold:
                    # Keep as fallback if YOLO is confident enough despite appearance rejection
                    if self.fallback_conf_threshold is not None and conf > self.fallback_conf_threshold and conf > fallback_conf:
                        fallback_conf = conf
                        fallback_coords = (x1, y1, x2, y2)
                    rejected = True

            if rejected:
                continue

            # Keep only the highest-confidence box that passed all filters
            if conf > best_conf:
                best_conf = conf
                best_coords = (x1, y1, x2, y2)

        # Fallback: use high-confidence detection even if appearance gate rejected it
        if best_coords is None and fallback_coords is not None:
            best_coords = fallback_coords
            best_conf = fallback_conf
            best_is_fallback = True

        # --- Annotate ---
        if best_coords is not None:
            x1, y1, x2, y2 = best_coords
            cv.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv.putText(
                annotated,
                f"PHONE {best_conf:.0%}",
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

        # --- Eye / gaze tracking (frame-skipped) ---
        # On active frames, run MediaPipe and cache the result.
        # On skipped frames, reuse the last annotated overlay.
        if run_detectors or self._last_gaze_annotated is None:
            self._last_gaze_annotated = self.eye_tracker.track_eyes(annotated)
        annotated = self._last_gaze_annotated

        # --- Distraction event logging ---
        # Fallback detections are intentionally visual-only; they help with overlay
        # continuity but are not trusted enough to suppress/look-away logging.
        phone_detected_for_tracking = best_coords is not None and not best_is_fallback
        self._update_distraction_tracking(phone_detected_for_tracking)

        # --- Attention UI state (3-state: ATTENTIVE / LOOK_AWAY / LEFT_DESK) ---
        # We draw this in camera.py (instead of attention_tracker.py) because LEFT_DESK
        # depends on distraction-transition timing managed here.
        attention_data = self.eye_tracker._cached_data
        ui_state, ui_color = self._get_attention_ui_state(attention_data)
        cv.putText(
            annotated,
            f"Attention: {ui_state}",
            (30, 135),
            cv.FONT_HERSHEY_SIMPLEX,
            0.65,
            ui_color,
            2,
        )

        return frame, annotated

    def _get_attention_ui_state(self, attention_data: dict) -> tuple[str, tuple[int, int, int]]:
        """Return a user-facing 3-state attention label for the on-frame overlay.

        States:
        - ATTENTIVE: face present and facing screen.
        - LOOK_AWAY: face present but not facing screen, OR face absent for < LEFT_DESK threshold.
        - LEFT_DESK: face has been continuously absent for >= _LEFT_DESK_TRANSITION_SECONDS.

        UI state is driven by *current sensor data*, not by the distraction tracking cooldown.
        _left_desk_distraction_start / _look_away_distraction_start stay open during their
        cooldown windows (so the logger can merge flickers into one event) but that must NOT
        bleed into the attention overlay — the user should see ATTENTIVE the moment their face
        returns and is facing the screen.
        """
        face_present = attention_data.get("face_present", True)
        face_facing_screen = attention_data.get("face_facing_screen", True)

        # Face back and looking at the screen → immediately attentive regardless of any
        # open cooldown on the tracking side.
        if face_present and face_facing_screen:
            return "ATTENTIVE", (0, 220, 0)

        # No face: LEFT_DESK only after the continuous-absence timer has fired.
        if not face_present:
            if self._no_face_since is not None and (
                time.time() - self._no_face_since >= self._LEFT_DESK_TRANSITION_SECONDS
            ):
                return "LEFT_DESK", (0, 0, 255)
            return "LOOK_AWAY", (0, 165, 255)

        # Face present but not facing screen.
        return "LOOK_AWAY", (0, 165, 255)

    def _update_distraction_tracking(self, phone_detected: bool) -> None:
        """Track distraction events with cooldown merging and priority suppression.

        Cooldown: when a trigger disappears, the event stays open for
        ``_DISTRACTION_COOLDOWN`` seconds.  If the trigger reappears inside
        that window, the event continues seamlessly.  Duration is measured
        from start to last-seen (not start to cooldown-expiry).

        Priority: phone distraction outranks look-away/left-desk only while
        they overlap in the same frame. Once phone is no longer detected,
        non-phone tracking can continue immediately (phone cooldown does not
        suppress other types).
        """
        distraction_type = _get_distraction_type()
        if self._session_manager is None or distraction_type is None:
            return

        now = time.time()
        attention_data = self.eye_tracker._cached_data
        face_present = attention_data.get("face_present", True)
        # Use a single "away" signal so no-face and face-not-facing share one timeline.
        # If the no-face segment stays continuous long enough, we promote that same
        # ongoing event from LOOK_AWAY to LEFT_DESK.
        looking_away = not attention_data.get("face_facing_screen", True)
        left_desk = not face_present  # True when MediaPipe detects no face at all

        # --- Phone distraction (highest priority) ---
        if phone_detected:
            if self._phone_distraction_start is None:
                self._phone_distraction_start = now  # open a new event on first detection
                if self._on_distraction_started:
                    self._on_distraction_started("PHONE_DISTRACTION")
            self._phone_last_seen = now  # keep refreshing so the cooldown resets each frame
        elif self._phone_distraction_start is not None:
            # Phone is gone but the event is still open — wait out the cooldown before logging.
            # This merges flickers (phone briefly leaves then returns) into a single event.
            if now - self._phone_last_seen >= self._DISTRACTION_COOLDOWN:
                # Cooldown expired: duration is start → last_seen, NOT start → now,
                # so the 5s wait doesn't inflate the reported distraction length.
                duration = max(1, int(self._phone_last_seen - self._phone_distraction_start))
                try:
                    self._session_manager.log_distraction(distraction_type.PHONE_DISTRACTION, duration)
                except Exception:
                    pass  # Session may not be IN_PROGRESS; never crash the camera loop
                self._phone_distraction_start = None
                self._phone_last_seen = None

        # --- Same-frame priority suppression (phone wins only on overlap) ---
        # If phone is currently detected, finalize any open non-phone event up to its
        # own last_seen boundary, then skip non-phone tracking for this frame only.
        # This avoids double-counting overlapping moments without suppressing unrelated
        # look-away/left-desk events during the phone cooldown window.
        if phone_detected:
            if self._look_away_distraction_start is not None:
                end = self._look_away_last_seen or now
                duration = max(1, int(end - self._look_away_distraction_start))
                try:
                    self._session_manager.log_distraction(distraction_type.LOOK_AWAY_DISTRACTION, duration)
                except Exception:
                    pass
                self._look_away_distraction_start = None
                self._look_away_last_seen = None

            if self._left_desk_distraction_start is not None:
                end = self._left_desk_last_seen or now
                duration = max(1, int(end - self._left_desk_distraction_start))
                try:
                    self._session_manager.log_distraction(distraction_type.LEFT_DESK_DISTRACTION, duration)
                except Exception:
                    pass
                self._left_desk_distraction_start = None
                self._left_desk_last_seen = None
            return

        # --- Left-desk as a transition from look-away ---
        # Policy: no-face segments start as LOOK_AWAY. If the face is *continuously absent*
        # for _LEFT_DESK_TRANSITION_SECONDS, the ongoing event is promoted to LEFT_DESK.
        # The timer (_no_face_since) starts only when the face first disappears and resets
        # whenever the face returns — prior face-present look-away time does NOT count.
        if left_desk:
            if self._no_face_since is None:
                self._no_face_since = now  # first frame with no face in this absence

            if self._left_desk_distraction_start is None:
                # Keep the look-away event open while we wait for the promotion threshold.
                if self._look_away_distraction_start is None:
                    self._look_away_distraction_start = now
                    if self._on_distraction_started:
                        self._on_distraction_started("LOOK_AWAY_DISTRACTION")
                self._look_away_last_seen = now

                # Promote only once the face has been continuously absent for the full threshold.
                if now - self._no_face_since >= self._LEFT_DESK_TRANSITION_SECONDS:
                    self._left_desk_distraction_start = self._look_away_distraction_start
                    self._left_desk_last_seen = now
                    self._look_away_distraction_start = None
                    self._look_away_last_seen = None
                    if self._on_distraction_started:
                        self._on_distraction_started("LEFT_DESK_DISTRACTION")
            else:
                # Already transitioned; keep extending the left-desk event.
                self._left_desk_last_seen = now
        else:
            # Face present again: reset the no-face timer unconditionally.
            self._no_face_since = None

            # Finalize any open LEFT_DESK event after cooldown.
            if self._left_desk_distraction_start is not None:
                if now - self._left_desk_last_seen >= self._DISTRACTION_COOLDOWN:
                    duration = max(1, int(self._left_desk_last_seen - self._left_desk_distraction_start))
                    try:
                        self._session_manager.log_distraction(distraction_type.LEFT_DESK_DISTRACTION, duration)
                    except Exception:
                        pass
                    self._left_desk_distraction_start = None
                    self._left_desk_last_seen = None

            # Normal look-away tracking (face present but not facing screen).
            if looking_away:
                if self._look_away_distraction_start is None:
                    self._look_away_distraction_start = now
                    if self._on_distraction_started:
                        self._on_distraction_started("LOOK_AWAY_DISTRACTION")
                self._look_away_last_seen = now
            elif self._look_away_distraction_start is not None:
                if now - self._look_away_last_seen >= self._DISTRACTION_COOLDOWN:
                    duration = max(1, int(self._look_away_last_seen - self._look_away_distraction_start))
                    try:
                        self._session_manager.log_distraction(distraction_type.LOOK_AWAY_DISTRACTION, duration)
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
        distraction_type = _get_distraction_type()
        if self._session_manager is None or distraction_type is None:
            return

        if self._phone_distraction_start is not None:
            # Use last_seen as the end boundary — the camera is shutting down, not
            # the phone disappearing, so we don't want to pad with cooldown time.
            end = self._phone_last_seen or time.time()
            duration = max(1, int(end - self._phone_distraction_start))
            try:
                self._session_manager.log_distraction(distraction_type.PHONE_DISTRACTION, duration)
            except Exception:
                pass
            self._phone_distraction_start = None
            self._phone_last_seen = None

        if self._look_away_distraction_start is not None:
            end = self._look_away_last_seen or time.time()  # same rationale as phone flush above
            duration = max(1, int(end - self._look_away_distraction_start))
            try:
                self._session_manager.log_distraction(distraction_type.LOOK_AWAY_DISTRACTION, duration)
            except Exception:
                pass
            self._look_away_distraction_start = None
            self._look_away_last_seen = None

        if self._left_desk_distraction_start is not None:
            end = self._left_desk_last_seen or time.time()  # same rationale as phone flush above
            duration = max(1, int(end - self._left_desk_distraction_start))
            try:
                self._session_manager.log_distraction(distraction_type.LEFT_DESK_DISTRACTION, duration)
            except Exception:
                pass
            self._left_desk_distraction_start = None
            self._left_desk_last_seen = None

        self._no_face_since = None


# Runs only when camera.py is executed directly
if __name__ == "__main__":
    cam = Camera()
    # Calibration is intentionally menu-driven (see vision/menu.py).
    # Running camera.py directly starts detection immediately.
    while True:
        data = cam.read_frame()
        if data is None:
            break
        _, annotated = data
        cv.imshow("Phone Detection", annotated)
        if cv.waitKey(1) == ord("q"):
            break
    cam.release()
