import cv2
import numpy as np
import os
import time
from ultralytics import YOLO


class PhoneCalibration:
    """Interactive helper that tunes phone-detection settings for the current user/environment."""

    def __init__(self, model_path: str = "yolo26n.pt"):
        self.model = YOLO(model_path)  # Load the base detector once and reuse it for all calibration steps.
        # __file__ is now detectors/phone_calibration.py; go up one level to reach the vision root
        self.animations_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "animations")
        self.few_shot_bundle_path = os.path.join(os.path.dirname(__file__), "..", "phone_few_shot_bundle.npz")
        self._animation_frames_cache = {}  # Stores per-direction rendered frame sequences.
        # [INTELLIGENCE TEAM] calibration_data is the primary output of the calibration process.
        # get_optimal_params() packages these values into runtime detection settings for the
        # phone-detection pipeline. Keys include confidence thresholds, lighting quality, and
        # per-phase appearance similarity gates.
        self.calibration_data = {
            "avg_confidence": 0.0,  # Mean confidence across accepted calibration samples.
            "optimal_conf_threshold": 0.5,  # Default fallback until calibration computes a better threshold.
            "detections_count": 0,  # Number of accepted samples collected during calibration.
            "few_shot_samples": 0,  # Number of appearance exemplars captured during steady phase.
            "few_shot_similarity_threshold": 0.30,  # Global fallback similarity gate.
            "few_shot_similarity_thresholds": {
                "steady": 0.30,
                "right_rotation": 0.27,
                "left_rotation": 0.27,
            },
            "lighting_quality": "unknown",  # Qualitative label derived from average confidence.
            "calibrated": False,  # Flips to True only after enough usable samples are collected.
        }

    @staticmethod
    def get_few_shot_bundle_path() -> str:
        """Return the persisted few-shot bundle path shared by calibrator and runtime camera."""
        # Bundle lives at the vision root (one level up from detectors/) so calibrator
        # and camera.py both resolve to the same shared file.
        return os.path.join(os.path.dirname(__file__), "..", "phone_few_shot_bundle.npz")

    def _load_rotation_frames(self, direction: str) -> list:
        """Load and cache frames from the GIF rotation guide for this direction."""
        if direction in self._animation_frames_cache:
            return self._animation_frames_cache[direction]

        gif_name = "rotate_phone_right.gif" if direction == "right" else "rotate_phone_left.gif"
        gif_path = os.path.join(self.animations_dir, gif_name)
        if not os.path.exists(gif_path):
            self._animation_frames_cache[direction] = []
            return []

        frames = []
        try:
            from PIL import Image, ImageSequence

            with Image.open(gif_path) as gif:
                for gif_frame in ImageSequence.Iterator(gif):
                    # Convert to RGBA first so transparent GIF pixels are composited predictably.
                    rgba = gif_frame.convert("RGBA")
                    bg = Image.new("RGBA", rgba.size, (18, 18, 18, 255))
                    composed = Image.alpha_composite(bg, rgba)

                    # OpenCV expects BGR; convert from PIL RGB before fitting.
                    bgr = cv2.cvtColor(np.asarray(composed.convert("RGB")), cv2.COLOR_RGB2BGR)
                    frames.append(self._fit_preview_frame(bgr, width=220, height=220))
        except Exception:
            frames = []

        # Keep a readable fallback frame if decode fails.
        if not frames:
            fallback = np.full((220, 220, 3), 20, dtype=np.uint8)
            cv2.putText(fallback, "Preview unavailable", (20, 112),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA)
            frames = [fallback]

        self._animation_frames_cache[direction] = frames
        return frames

    def _fit_preview_frame(self, frame, width: int, height: int):
        """Resize preview frame with letterboxing so aspect ratio is preserved."""
        h, w = frame.shape[:2]
        if h <= 0 or w <= 0:
            return np.full((height, width, 3), 20, dtype=np.uint8)

        scale = min(width / w, height / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        canvas = np.full((height, width, 3), 18, dtype=np.uint8)
        x = (width - new_w) // 2
        y = (height - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized
        return canvas

    def _draw_rotation_preview(self, frame, direction: str, elapsed_seconds: float):
        """Overlay the right/left GIF preview in the calibration frame."""
        # [UX/UI TEAM] Animated GIF panel shows users exactly how to rotate the phone.
        # Panel is positioned top-right so it does not overlap the guide box or the
        # progress/appearance-score text at the bottom of the frame.
        frames = self._load_rotation_frames(direction)
        preview = None
        if frames:
            fps = 8.0  # Preview playback speed for guidance.
            idx = int((elapsed_seconds * fps) % len(frames))
            preview = frames[idx]
        h, w = frame.shape[:2]

        panel_w, panel_h = 236, 260
        # Place guide animation out of the center guide box (top-left corner), not right-center.
        x1 = 12
        y1 = 12
        x2 = min(w - 12, x1 + panel_w)
        y2 = min(h - 12, y1 + panel_h)

        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 255), 2)

        title = "ROTATE RIGHT" if direction == "right" else "ROTATE LEFT"
        cv2.putText(frame, title, (x1 + 8, y1 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
        cv2.putText(frame, "(your view, not camera)", (x1 + 8, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (160, 160, 160), 1)

        if preview is not None and (y1 + 32 + preview.shape[0]) <= y2:
            py1 = y1 + 32
            py2 = py1 + preview.shape[0]
            px1 = x1 + 8
            px2 = px1 + preview.shape[1]
            frame[py1:py2, px1:px2] = preview
        else:
            cv2.putText(frame, "Preview unavailable", (x1 + 24, y1 + 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)
            cv2.putText(frame, "Could not decode GIF", (x1 + 26, y1 + 158),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    def _get_guide_box(self, frame_shape):
        """Return a centered guide box where the phone should be placed."""
        height, width = frame_shape[:2]  # OpenCV frame shape is (height, width, channels).
        box_width = int(width * 0.224)  # Narrow width keeps the phone close to frame center during setup.
        box_height = int(height * 0.47)  # Taller box fits a vertical phone and small hand movement.
        x1 = (width - box_width) // 2  # Left edge of centered guide box.
        y1 = (height - box_height) // 2  # Top edge of centered guide box.
        x2 = x1 + box_width  # Right edge derived from left edge + width.
        y2 = y1 + box_height  # Bottom edge derived from top edge + height.
        return x1, y1, x2, y2

    def _draw_guide_box(self, frame, active=False):
        """Draw the phone placement guide box."""
        # [UX/UI TEAM] Color signals detection state to the user:
        # yellow = waiting for alignment, green = phone locked in.
        # Dimensions are computed relative to frame size in _get_guide_box() so the
        # box scales correctly across different camera resolutions.
        x1, y1, x2, y2 = self._get_guide_box(frame.shape)
        color = (0, 255, 0) if active else (0, 255, 255)  # Green = locked in, yellow = waiting for alignment.
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)  # Draw the actual placement target.
        cv2.putText(frame, "Place phone inside box", (x1 - 15, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        return x1, y1, x2, y2

    def _find_phone_in_box(self, frame, conf=0.15):
        """Return the strongest phone detection and whether it is centered in the guide box."""
        results = self.model(frame, classes=[67], conf=conf, verbose=False)  # Class 67 is COCO's cell phone label.
        boxes = results[0].boxes  # YOLO returns all detections for the frame here.
        if not boxes:
            return None, False, results

        best_box = max(boxes, key=lambda box: float(box.conf[0]))  # Keep only the strongest phone candidate.
        x1, y1, x2, y2 = map(int, best_box.xyxy[0])  # Convert tensor coordinates into plain pixel ints.
        guide_x1, guide_y1, guide_x2, guide_y2 = self._get_guide_box(frame.shape)
        center_x = (x1 + x2) // 2  # Horizontal center of detected phone box.
        center_y = (y1 + y2) // 2  # Vertical center of detected phone box.
        in_box = guide_x1 <= center_x <= guide_x2 and guide_y1 <= center_y <= guide_y2  # True only if box center falls inside the guide.
        return best_box, in_box, results

    def _box_metrics(self, best_box, frame_shape):
        """Return normalized geometry values used for phase validation."""
        # [INTELLIGENCE TEAM] All values are normalized to [0, 1] so they are
        # camera-resolution-agnostic — downstream models can compare them directly
        # without adjusting for different capture resolutions.
        h, w = frame_shape[:2]
        x1, y1, x2, y2 = map(int, best_box.xyxy[0])
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        return {
            "center_x_norm": ((x1 + x2) / 2) / w,
            "center_y_norm": ((y1 + y2) / 2) / h,
            "width_norm": bw / w,
            "height_norm": bh / h,
            "area_ratio": (bw * bh) / float(w * h),
            "aspect_ratio": bh / float(bw),
        }

    def _extract_phone_crop(self, frame, best_box, pad_ratio: float = 0.12):
        """Crop the detected phone region with a small margin for appearance modeling."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, best_box.xyxy[0])
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

    def _normalize_crop_for_bundle(self, crop, size: int = 96):
        """Convert an arbitrary crop into a compact fixed-size exemplar image."""
        if crop is None or crop.size == 0:
            return None
        return cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)

    def _compute_few_shot_signature(self, crop) -> np.ndarray:
        """Create a compact, normalized appearance signature from a phone crop."""
        # [INTELLIGENCE TEAM] The 257-element signature (256 H/S histogram bins +
        # 1 edge-density scalar) is unit-normed so a dot product directly equals
        # cosine similarity. This is the core appearance descriptor used to verify a
        # detection actually matches the user's specific device across rotations.
        if crop is None or crop.size == 0:
            return None

        resized = cv2.resize(crop, (96, 96), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        # 2D color histogram over Hue/Saturation gives a robust appearance descriptor.
        hist_hs = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256]).flatten().astype(np.float32)
        hist_hs /= (float(hist_hs.sum()) + 1e-6)

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 160)
        edge_ratio = np.array([float(np.count_nonzero(edges)) / edges.size], dtype=np.float32)

        sig = np.concatenate([hist_hs, edge_ratio], axis=0)
        norm = float(np.linalg.norm(sig))
        if norm < 1e-8:
            return None
        return sig / norm

    def _few_shot_similarity(self, signature: np.ndarray, exemplars: list) -> float:
        """Return max cosine similarity against learned appearance exemplars."""
        # [INTELLIGENCE TEAM] Max-similarity (1-nearest-neighbour) keeps matching
        # tolerant across the full range of viewpoints collected during calibration.
        # Improving exemplar bank diversity raises precision without needing a
        # stricter gate value.
        if signature is None or not exemplars:
            return 0.0
        sims = [float(np.dot(signature, ex)) for ex in exemplars if ex is not None]
        return max(sims) if sims else 0.0

    def _estimate_few_shot_threshold(self, exemplars: list) -> float:
        """Estimate a conservative similarity gate from exemplar self-consistency."""
        # [INTELLIGENCE TEAM] The gate auto-tunes: a visually consistent exemplar
        # bank yields a higher inter-exemplar median and therefore a tighter gate.
        # A diverse bank (many viewpoints) returns a looser gate to stay inclusive.
        if len(exemplars) < 3:
            return 0.30
        sims = []
        for i in range(len(exemplars)):
            for j in range(i + 1, len(exemplars)):
                sims.append(float(np.dot(exemplars[i], exemplars[j])))
        if not sims:
            return 0.45
        # Margin below median keeps the gate tolerant to moderate rotation/lighting shifts.
        return float(np.clip(np.median(sims) - 0.05, 0.25, 0.85))

    def _add_signature_if_novel(self, bank: list, signature: np.ndarray, max_count: int = 14) -> bool:
        """Append signature only if it adds view diversity to the bank."""
        if signature is None or len(bank) >= max_count:
            return False
        if not bank:
            bank.append(signature)
            return True

        max_sim = max(float(np.dot(signature, ex)) for ex in bank)
        # Reject near-duplicates so we keep coverage across different viewpoints.
        if max_sim >= 0.985:
            return False
        bank.append(signature)
        return True

    def _phase_exemplars(self, few_shot_banks: dict, phase_kind: str) -> list:
        """Return exemplar pool used for appearance matching in a phase."""
        pool = list(few_shot_banks.get("steady", []))
        if phase_kind in ("right_rotation", "left_rotation"):
            pool.extend(few_shot_banks.get(phase_kind, []))
        return pool

    def _save_few_shot_bundle(self, few_shot_banks: dict, crop_banks: dict, few_shot_thresholds: dict):
        """Persist few-shot exemplars and thresholds to a single overwriteable bundle file."""
        signatures = []
        images = []
        phase_labels = []

        for phase_name in ("steady", "right_rotation", "left_rotation"):
            sig_bank = few_shot_banks.get(phase_name, [])
            img_bank = crop_banks.get(phase_name, [])
            count = min(len(sig_bank), len(img_bank))
            for idx in range(count):
                signatures.append(sig_bank[idx])
                images.append(img_bank[idx])
                phase_labels.append(phase_name)

        if not signatures or not images:
            return False

        np.savez_compressed(
            self.few_shot_bundle_path,
            signatures=np.asarray(signatures, dtype=np.float32),
            images=np.asarray(images, dtype=np.uint8),
            phases=np.asarray(phase_labels, dtype="U16"),
            threshold_steady=np.float32(few_shot_thresholds.get("steady", 0.45)),
            threshold_right=np.float32(few_shot_thresholds.get("right_rotation", 0.42)),
            threshold_left=np.float32(few_shot_thresholds.get("left_rotation", 0.42)),
            threshold_global=np.float32(
                min(
                    few_shot_thresholds.get("steady", 0.45),
                    few_shot_thresholds.get("right_rotation", 0.42),
                    few_shot_thresholds.get("left_rotation", 0.42),
                )
            ),
            conf_threshold=np.float32(self.calibration_data.get("optimal_conf_threshold", 0.35)),
            updated_at=np.int64(time.time()),
        )
        return True

    def _sync_thresholds_to_settings(self):
        """Write calibration-derived phone thresholds to settings.json.

        Called after a successful calibration so the Settings UI reflects the
        newly computed values without requiring a manual entry.
        """
        try:
            from src.core import settings_manager
        except ImportError:
            return

        conf = self.calibration_data.get("optimal_conf_threshold")
        similarity = self.calibration_data.get("few_shot_similarity_threshold")
        fallback = min(1.0, conf + 0.15) if conf is not None else None

        settings = settings_manager.load()
        thresholds = settings.get("detection_thresholds", {})
        if conf is not None:
            thresholds["yolo_conf"] = round(conf, 3)
        if similarity is not None:
            thresholds["few_shot_similarity"] = round(similarity, 3)
        if fallback is not None:
            thresholds["fallback_conf"] = round(fallback, 3)
        settings["detection_thresholds"] = thresholds
        settings_manager.save(settings)

    def _rotation_valid(self, metrics, baseline, direction, phase_start_x):
        """Heuristic check for side rotation. This is a proxy, not a perfect 3D angle measurement."""
        # Right/left rotation makes the visible phone face appear narrower and smaller.
        # Using 0.82 (was 0.72) so a partial rotation still counts as valid.
        narrow_enough = metrics["width_norm"] <= baseline["width_norm"] * 0.82
        area_reduced = metrics["area_ratio"] <= baseline["area_ratio"] * 0.82

        # 0.02 drift (was 0.04) — accept smaller lateral movement so tall/close phones still pass.
        drift = metrics["center_x_norm"] - phase_start_x
        drift_ok = drift >= 0.02 if direction == "right" else drift <= -0.02

        # Accept if the phone clearly looks edge-on plus directional movement.
        return (narrow_enough or area_reduced) and drift_ok

    def _wait_for_phone_in_box(self, cap, hold_seconds=1.0):
        """Wait until the user places the phone in the guide box steadily."""
        # [UX/UI TEAM] The 1.0 s hold requirement prevents an accidental pass through
        # the box from triggering calibration. The on-screen countdown ("Hold steady: Xs")
        # gives the user explicit feedback on how long they need to hold.
        stable_since = None  # Timestamp marking when the phone first became valid and centered.

        while True:
            ret, frame = cap.read()
            if not ret:
                return {"error": "Could not read camera frame"}

            # Keep a clean capture copy for detection so on-screen UI overlays cannot be detected as a phone.
            raw_frame = frame.copy()

            height, width = frame.shape[:2]
            overlay = frame.copy()  # Draw overlays on a copy first so text remains readable.
            cv2.rectangle(overlay, (0, 0), (width, 105), (0, 0, 0), -1)  # Dark banner behind top instructions.
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)  # Blend overlay back onto the live frame.

            box = self._draw_guide_box(frame, active=stable_since is not None)
            guide_x1, guide_y1, guide_x2, guide_y2 = box

            best_box, in_box, _ = self._find_phone_in_box(raw_frame, conf=0.15)  # Use low threshold during setup to avoid missing borderline poses.

            cv2.putText(frame, "CALIBRATION READY", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            cv2.putText(frame, "Place your phone inside the box to begin", (10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Tip: Hold phone with one hand from the bottom", (10, 88),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (190, 230, 255), 1)
            cv2.putText(frame, "Press Q to cancel", (10, 103),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            if best_box is not None:
                x1, y1, x2, y2 = map(int, best_box.xyxy[0])
                conf = float(best_box.conf[0])
                color = (0, 255, 0) if in_box else (0, 165, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, f"PHONE {conf:.0%}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                if in_box:
                    if stable_since is None:
                        stable_since = time.time()  # Start hold timer only on the first valid centered frame.
                    held_for = time.time() - stable_since  # Total time the phone has stayed centered.
                    remaining = max(0.0, hold_seconds - held_for)  # Clamp at zero so the countdown never goes negative.
                    cv2.putText(frame, f"Hold steady to start: {remaining:.1f}s", (guide_x1 - 10, guide_y2 + 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    if held_for >= hold_seconds:
                        cv2.imshow("Phone Calibration", frame)
                        cv2.waitKey(250)
                        return {"success": True}
                else:
                    stable_since = None  # Reset hold timer if the phone leaves the guide box.
                    cv2.putText(frame, "Center the phone inside the box", (guide_x1 - 5, guide_y2 + 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            else:
                stable_since = None  # Reset hold timer if no phone is detected at all.
                cv2.putText(frame, "No phone detected yet", (guide_x1 + 5, guide_y2 + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("Phone Calibration", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                return {"error": "Calibration cancelled"}

    def _capture_rotation_snapshot(
        self,
        cap,
        current_frame,
        phase_kind: str,
        baseline: dict,
        few_shot_banks: dict,
        crop_banks: dict,
        few_shot_thresholds: dict,
        burst_count: int = 8,
        burst_interval_ms: int = 80,
    ) -> int:
        """Capture a quick burst of frames when the user presses SPACE during a rotation phase.

        Instead of relying on the continuous frame-by-frame validator to catch the
        phone at just the right angle, this lets the user *intentionally* freeze at
        the desired rotation and trigger a burst capture.  The burst uses a lower
        YOLO confidence threshold and a more lenient rotation check so angled phones
        with unusual cases are much more likely to be accepted.

        Args:
            cap: OpenCV VideoCapture already open.
            current_frame: The live frame at the moment SPACE was pressed (included in burst).
            phase_kind: ``"right_rotation"`` or ``"left_rotation"``.
            baseline: Geometry baseline dict from the steady phase.
            few_shot_banks / crop_banks / few_shot_thresholds: Mutated in place.
            burst_count: Number of frames to capture.
            burst_interval_ms: Delay between captures (ms).

        Returns:
            Number of valid frames collected (added to ``valid_frames`` in caller).
        """
        # Collect burst frames — first is the frame already on screen when SPACE hit.
        burst_frames = [current_frame]
        for _ in range(burst_count - 1):
            ret, f = cap.read()
            if ret:
                burst_frames.append(f.copy())
            cv2.waitKey(burst_interval_ms)

        # Flash "Capturing…" so the user knows their press registered.
        show = burst_frames[0].copy()
        h_s, w_s = show.shape[:2]
        cv2.putText(
            show, "Capturing...", (w_s // 2 - 120, h_s // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2, cv2.LINE_AA,
        )
        cv2.imshow("Phone Calibration", show)
        cv2.waitKey(1)

        phase_exemplars = self._phase_exemplars(few_shot_banks, phase_kind)
        phase_threshold = few_shot_thresholds.get(phase_kind, 0.42)
        valid_count = 0

        for bf in burst_frames:
            # Lower threshold here so angled / unusual-case phones aren't missed.
            best_box, in_box, _ = self._find_phone_in_box(bf, conf=0.15)
            if best_box is None or not in_box:
                continue

            metrics = self._box_metrics(best_box, bf.shape)

            # Relaxed rotation check: size/area reduction vs baseline is enough —
            # we trust the user pressed SPACE at the right angle, so skip drift gating.
            if baseline is not None:
                size_ok = (
                    metrics["width_norm"] <= baseline["width_norm"] * 0.85
                    or metrics["area_ratio"] <= baseline["area_ratio"] * 0.85
                )
                if not size_ok:
                    continue

            # Appearance similarity — more lenient than the continuous path so
            # partially-turned phones still enrich the exemplar bank.
            if phase_exemplars:
                crop = self._extract_phone_crop(bf, best_box)
                sig = self._compute_few_shot_signature(crop)
                score = self._few_shot_similarity(sig, phase_exemplars)
                if score < max(0.22, phase_threshold - 0.18):
                    continue

            # Valid frame — add to exemplar bank if it adds new view diversity.
            crop = self._extract_phone_crop(bf, best_box)
            sig = self._compute_few_shot_signature(crop)
            added = self._add_signature_if_novel(few_shot_banks[phase_kind], sig, max_count=12)
            if added:
                norm_crop = self._normalize_crop_for_bundle(crop)
                if norm_crop is not None:
                    crop_banks[phase_kind].append(norm_crop)
            valid_count += 1

        # Re-estimate threshold from the enriched bank.
        bank = few_shot_banks[phase_kind]
        if len(bank) >= 3:
            updated = self._estimate_few_shot_threshold(bank)
            few_shot_thresholds[phase_kind] = float(np.clip(updated - 0.03, 0.30, 0.82))

        # Brief result overlay so the user knows whether the snapshot counted.
        result_frame = burst_frames[-1].copy()
        h_r, w_r = result_frame.shape[:2]
        if valid_count >= 3:
            msg = f"Snapshot OK — {valid_count}/{burst_count} frames valid"
            color = (0, 255, 100)
        else:
            msg = f"Only {valid_count} valid — rotate farther and press SPACE again"
            color = (0, 100, 255)
        cv2.putText(
            result_frame, msg, (20, h_r // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2, cv2.LINE_AA,
        )
        cv2.imshow("Phone Calibration", result_frame)
        cv2.waitKey(900)

        return valid_count

    def _prompt_retry_or_quit(self, cap, phase_name: str) -> str:
        """
        Freeze the feed and show a timeout screen.
        Returns 'retry' to redo the current phase, or 'quit' to abort.
        """
        # [UX/UI TEAM] The 0.55 dim overlay ensures prompt text is legible regardless
        # of what was in the live frame. [R]/[Q] keys are shown on-screen so users
        # do not need to remember bindings from the earlier calibration screens.
        while True:
            ret, frame = cap.read()
            if not ret:
                return "quit"

            h, w = frame.shape[:2]

            # Dim the frame so the prompt stands out.
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

            cv2.putText(frame, f"{phase_name} TIMED OUT", (w // 2 - 180, h // 2 - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2)
            cv2.putText(frame, "Rotate farther and keep the phone inside the box.",
                        (w // 2 - 260, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, "Press [R] to retry this phase   [Q] to quit",
                        (w // 2 - 240, h // 2 + 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

            cv2.imshow("Phone Calibration", frame)
            key = cv2.waitKey(30) & 0xFF
            if key == ord('r'):
                return "retry"
            if key == ord('q'):
                return "quit"

    def run_calibration(self, target_detections: int = 15) -> dict:
        """
        Interactive multi-phase calibration with auto-start and clear rotation prompts.
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return {"error": "Cannot open camera"}

        ready_result = self._wait_for_phone_in_box(cap)
        if ready_result.get("error"):
            cap.release()
            cv2.destroyAllWindows()
            return ready_result

        confidences = []  # Stores only accepted sample confidences used to compute the final threshold.
        baseline_metrics = []
        baseline = None
        few_shot_banks = {
            "steady": [],
            "right_rotation": [],
            "left_rotation": [],
        }
        crop_banks = {
            "steady": [],
            "right_rotation": [],
            "left_rotation": [],
        }
        few_shot_thresholds = {
            "steady": 0.45,
            "right_rotation": 0.42,
            "left_rotation": 0.42,
        }

        # Validation-first phases: each phase advances when enough valid frames are seen.
        # A timeout still exists so the user can retry instead of being stuck forever.
        phases = [
            {
                "name": "PHASE 1",
                "instruction": "Hold phone steady in the box",
                "required_valid_frames": 8,  # Lowered from 12 — fewer steady frames needed to baseline.
                "max_seconds": 20,
                "kind": "steady",
                "collect": True,
            },
            {
                "name": "PHASE 2",
                "instruction": "Rotate phone RIGHT about 90 degrees",
                "required_valid_frames": 5,  # Lowered from 7 — easier to hit with relaxed thresholds.
                "max_seconds": 25,
                "kind": "right_rotation",
                "collect": True,
            },
            {
                "name": "PHASE 3",
                "instruction": "Rotate phone LEFT about 90 degrees",
                "required_valid_frames": 5,  # Lowered from 7.
                "max_seconds": 25,
                "kind": "left_rotation",
                "collect": True,
            },
        ]

        for phase in phases:
            phase_start = time.time()
            valid_frames = 0
            phase_start_x = None
            rotation_phase = phase["kind"] in ("right_rotation", "left_rotation")
            recenter_ready = not rotation_phase
            recenter_hold_frames = 0
            recenter_required_frames = 5

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Get frame dimensions for centering text
                h, w = frame.shape[:2]
                
                # Draw semi-transparent overlay for better text visibility
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
                guide_box = self._draw_guide_box(frame)

                # Draw GIF rotation preview for rotation phases.
                if phase["kind"] in ("right_rotation", "left_rotation"):
                    direction = "right" if phase["kind"] == "right_rotation" else "left"
                    phase_elapsed = time.time() - phase_start
                    self._draw_rotation_preview(frame, direction, phase_elapsed)

                elapsed = time.time() - phase_start
                remaining = max(0, int(phase["max_seconds"] - elapsed))

                # Phase name and countdown
                cv2.putText(frame, phase["name"], (10, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                cv2.putText(frame, f"{remaining}s", (w - 70, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                
                # Main instruction
                cv2.putText(frame, phase["instruction"], (10, 75),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                if rotation_phase:
                    cv2.putText(frame, "Press SPACE to snapshot current angle",
                                (10, 97), cv2.FONT_HERSHEY_SIMPLEX, 0.52,
                                (140, 255, 180), 1, cv2.LINE_AA)
                
                # Run detection on the clean camera frame (not the UI-overlay frame).
                raw_frame = frame.copy()
                if phase["collect"]:
                    best_box, in_box, _ = self._find_phone_in_box(raw_frame, conf=0.15)
                    
                    if best_box is not None:
                        conf = float(best_box.conf[0])
                        metrics = self._box_metrics(best_box, frame.shape)
                        appearance_score = 0.0

                        # Rotation phases must start from a fresh centered pose.
                        if rotation_phase and baseline is not None and not recenter_ready:
                            centered_now = (
                                in_box
                                and metrics["aspect_ratio"] >= 1.1
                                and metrics["width_norm"] >= baseline["width_norm"] * 0.90
                                and metrics["area_ratio"] >= baseline["area_ratio"] * 0.85
                            )
                            if centered_now:
                                recenter_hold_frames += 1
                            else:
                                recenter_hold_frames = 0

                            cv2.putText(
                                frame,
                                f"Center first: {recenter_hold_frames}/{recenter_required_frames}",
                                (10, h - 78),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.65,
                                (0, 200, 255),
                                2,
                            )

                            if recenter_hold_frames >= recenter_required_frames:
                                recenter_ready = True
                                phase_start_x = metrics["center_x_norm"]

                        is_valid = False

                        if phase["kind"] == "steady":
                            # "Steady" means centered and still mostly upright.
                            is_valid = in_box and metrics["aspect_ratio"] >= 1.2
                            if is_valid:
                                baseline_metrics.append(metrics)
                                # Collect base exemplars from stable frames.
                                if valid_frames % 2 == 0:
                                    crop = self._extract_phone_crop(frame, best_box)
                                    sig = self._compute_few_shot_signature(crop)
                                    added = self._add_signature_if_novel(few_shot_banks["steady"], sig, max_count=14)
                                    if added:
                                        normalized = self._normalize_crop_for_bundle(crop)
                                        if normalized is not None:
                                            crop_banks["steady"].append(normalized)

                        elif phase["kind"] == "right_rotation" and baseline is not None and recenter_ready:
                            if phase_start_x is None:
                                phase_start_x = metrics["center_x_norm"]
                            appearance_ok = True
                            few_shot_pool = self._phase_exemplars(few_shot_banks, "right_rotation")
                            phase_threshold = few_shot_thresholds["right_rotation"]
                            if few_shot_pool:
                                crop = self._extract_phone_crop(frame, best_box)
                                sig = self._compute_few_shot_signature(crop)
                                appearance_score = self._few_shot_similarity(sig, few_shot_pool)
                                appearance_ok = appearance_score >= phase_threshold
                            rotation_ok = self._rotation_valid(metrics, baseline, "right", phase_start_x)
                            is_valid = in_box and rotation_ok and appearance_ok

                            # Online adaptation: while rotating, keep learning accepted new viewpoints.
                            if in_box and rotation_ok and few_shot_pool:
                                learn_cutoff = max(0.30, phase_threshold - 0.07)
                                if appearance_score >= learn_cutoff:
                                    crop = self._extract_phone_crop(frame, best_box)
                                    sig = self._compute_few_shot_signature(crop)
                                    added = self._add_signature_if_novel(few_shot_banks["right_rotation"], sig, max_count=12)
                                    if added:
                                        normalized = self._normalize_crop_for_bundle(crop)
                                        if normalized is not None:
                                            crop_banks["right_rotation"].append(normalized)
                                    if added and len(few_shot_banks["right_rotation"]) >= 3:
                                        updated = self._estimate_few_shot_threshold(few_shot_banks["right_rotation"])
                                        few_shot_thresholds["right_rotation"] = float(np.clip(updated - 0.03, 0.32, 0.82))

                        elif phase["kind"] == "left_rotation" and baseline is not None and recenter_ready:
                            if phase_start_x is None:
                                phase_start_x = metrics["center_x_norm"]
                            appearance_ok = True
                            few_shot_pool = self._phase_exemplars(few_shot_banks, "left_rotation")
                            phase_threshold = few_shot_thresholds["left_rotation"]
                            if few_shot_pool:
                                crop = self._extract_phone_crop(frame, best_box)
                                sig = self._compute_few_shot_signature(crop)
                                appearance_score = self._few_shot_similarity(sig, few_shot_pool)
                                appearance_ok = appearance_score >= phase_threshold
                            rotation_ok = self._rotation_valid(metrics, baseline, "left", phase_start_x)
                            is_valid = in_box and rotation_ok and appearance_ok

                            if in_box and rotation_ok and few_shot_pool:
                                learn_cutoff = max(0.30, phase_threshold - 0.07)
                                if appearance_score >= learn_cutoff:
                                    crop = self._extract_phone_crop(frame, best_box)
                                    sig = self._compute_few_shot_signature(crop)
                                    added = self._add_signature_if_novel(few_shot_banks["left_rotation"], sig, max_count=12)
                                    if added:
                                        normalized = self._normalize_crop_for_bundle(crop)
                                        if normalized is not None:
                                            crop_banks["left_rotation"].append(normalized)
                                    if added and len(few_shot_banks["left_rotation"]) >= 3:
                                        updated = self._estimate_few_shot_threshold(few_shot_banks["left_rotation"])
                                        few_shot_thresholds["left_rotation"] = float(np.clip(updated - 0.03, 0.32, 0.82))

                        if in_box:
                            confidences.append(conf)  # Keep only centered detections in the calibration sample set.

                        if is_valid:
                            valid_frames += 1

                        x1, y1, x2, y2 = map(int, best_box.xyxy[0])
                        color = (0, 255, 0) if in_box else (0, 165, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                        status_text = f"DETECTED {conf:.0%}" if in_box else "Move phone into box"
                        cv2.putText(frame, status_text, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                        progress_text = f"Validated: {valid_frames}/{phase['required_valid_frames']}"
                        cv2.putText(frame, progress_text, (10, h - 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        if phase["kind"] in ("right_rotation", "left_rotation"):
                            phase_threshold = few_shot_thresholds[phase["kind"]]
                            cv2.putText(
                                frame,
                                f"Appearance match: {appearance_score:.2f}/{phase_threshold:.2f}",
                                (10, h - 80),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (170, 240, 255),
                                2,
                            )
                    else:
                        # Red text when not detected
                        cv2.putText(frame, "No phone detected - place it inside the box", (10, h - 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Show running detection count
                cv2.putText(frame, f"Samples: {len(confidences)}", (w - 150, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                cv2.imshow("Phone Calibration", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return {"error": "Calibration cancelled"}
                elif key == ord(' ') and rotation_phase and baseline is not None:
                    # Snapshot capture: user manually triggers a burst at their chosen angle.
                    snap_valid = self._capture_rotation_snapshot(
                        cap, frame.copy(), phase["kind"], baseline,
                        few_shot_banks, crop_banks, few_shot_thresholds,
                    )
                    valid_frames += snap_valid

                # Move on only when validation requirements are met.
                if valid_frames >= phase["required_valid_frames"]:
                    if phase["kind"] == "steady" and baseline_metrics:
                        count = len(baseline_metrics)
                        baseline = {
                            "width_norm": sum(m["width_norm"] for m in baseline_metrics) / count,
                            "area_ratio": sum(m["area_ratio"] for m in baseline_metrics) / count,
                        }
                        few_shot_thresholds["steady"] = self._estimate_few_shot_threshold(few_shot_banks["steady"])
                        # Rotation views are naturally more variable, so start slightly lower than steady.
                        base_rot = float(np.clip(few_shot_thresholds["steady"] - 0.03, 0.32, 0.82))
                        few_shot_thresholds["right_rotation"] = base_rot
                        few_shot_thresholds["left_rotation"] = base_rot
                    break

                # On timeout, pause and let the user choose to retry the phase or quit.
                if elapsed >= phase["max_seconds"]:
                    choice = self._prompt_retry_or_quit(cap, phase["name"])
                    if choice == "retry":
                        # Reset phase state and try again without restarting the whole flow.
                        phase_start = time.time()
                        valid_frames = 0
                        phase_start_x = None
                        recenter_ready = not rotation_phase
                        recenter_hold_frames = 0
                        if phase["kind"] == "steady":
                            baseline_metrics.clear()  # Discard stale baseline samples before re-collecting.
                            few_shot_banks["steady"].clear()
                            crop_banks["steady"].clear()
                        else:
                            few_shot_banks[phase["kind"]].clear()
                            crop_banks[phase["kind"]].clear()
                        continue
                    else:
                        cap.release()
                        cv2.destroyAllWindows()
                        return {
                            "success": False,
                            "message": f"{phase['name']} validation failed.",
                            "suggestion": "Re-run calibration and rotate farther while keeping phone inside the box.",
                        }

        few_shot_total_samples = sum(len(v) for v in few_shot_banks.values())
        few_shot_global_threshold = min(
            few_shot_thresholds["steady"],
            few_shot_thresholds["right_rotation"],
            few_shot_thresholds["left_rotation"],
        )

        # Analyze results first
        result = self._analyze_calibration(
            confidences,
            target_detections,
            few_shot_sample_count=few_shot_total_samples,
            few_shot_similarity_threshold=few_shot_global_threshold,
            few_shot_similarity_thresholds=few_shot_thresholds,
        )  # Convert raw sample confidences into runtime settings.
        
        # If calibration succeeded, run validation
        if result.get("success"):
            validation = self._validate_calibration(cap)
            if validation == "retry":
                cap.release()
                cv2.destroyAllWindows()
                return self.run_calibration(target_detections)  # Restart the entire flow with a fresh camera session.
            elif validation == "cancel":
                cap.release()
                cv2.destroyAllWindows()
                return {"error": "Validation cancelled by user"}

            # Persist only after user accepted validation.
            result["few_shot_bundle_saved"] = self._save_few_shot_bundle(
                few_shot_banks,
                crop_banks,
                few_shot_thresholds,
            )
            result["few_shot_bundle_path"] = self.few_shot_bundle_path

            self._sync_thresholds_to_settings()
        
        cap.release()
        cv2.destroyAllWindows()

        return result
    
    def _validate_calibration(self, cap) -> str:
        """
        Let user verify detection is working with calibrated parameters.
        Returns: 'accept', 'retry', or 'cancel'
        """
        # [UX/UI TEAM] 10 s auto-accept keeps the flow moving for users who are
        # satisfied without pressing anything; [R] lets skeptical users restart.
        # [INTELLIGENCE TEAM] Detection here runs with the newly computed conf_threshold
        # so users see exactly the sensitivity the runtime pipeline will use.
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        
        conf_threshold = self.calibration_data["optimal_conf_threshold"]  # Threshold chosen by _analyze_calibration().
        validation_duration = 10  # seconds the user gets to verify the result before auto-accept.
        start_time = time.time()  # Validation timeout anchor.
        
        while time.time() - start_time < validation_duration:
            ret, frame = cap.read()
            if not ret:
                break
            
            h, w = frame.shape[:2]
            
            # Validation uses the threshold that calibration just produced so
            # the user sees the exact behavior that live detection would use.
            results = self.model(frame, classes=[67], conf=conf_threshold, verbose=False)  # Mirror live detection settings as closely as possible.
            
            # Draw header overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 110), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            self._draw_guide_box(frame)
            
            # Header text
            cv2.putText(frame, "VALIDATION - Rotate right, then left slowly", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, f"Threshold: {conf_threshold:.2f} | Lighting: {self.calibration_data['lighting_quality']}", 
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            cv2.putText(frame, "Press: [Y] Accept  |  [R] Retry  |  [Q] Cancel", (10, 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw detections
            if results[0].boxes:
                for box in results[0].boxes:
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    cv2.putText(frame, f"PHONE {conf:.0%}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # Success indicator
                cv2.putText(frame, "Detection working - keep rotations smooth", (10, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No phone detected - place it back in the box", (10, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Countdown
            remaining = int(validation_duration - (time.time() - start_time))  # Remaining auto-accept time.
            cv2.putText(frame, f"Auto-accept in {remaining}s", (w - 200, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            cv2.imshow("Phone Calibration", frame)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('y'):
                return "accept"
            elif key == ord('r'):
                return "retry"
            elif key == ord('q'):
                return "cancel"
        
        # Auto-accept keeps the flow moving if the user is satisfied and does
        # not explicitly press a key during the validation window.
        return "accept"

    def _analyze_calibration(
        self,
        confidences: list,
        target: int,
        few_shot_sample_count: int = 0,
        few_shot_similarity_threshold: float = 0.45,
        few_shot_similarity_thresholds: dict = None,
    ) -> dict:
        """Analyze collected data and set optimal parameters."""
        if few_shot_similarity_thresholds is None:
            few_shot_similarity_thresholds = {
                "steady": few_shot_similarity_threshold,
                "right_rotation": few_shot_similarity_threshold,
                "left_rotation": few_shot_similarity_threshold,
            }
        
        if len(confidences) < target:
            self.calibration_data["calibrated"] = False
            self.calibration_data["lighting_quality"] = "poor"
            self.calibration_data["few_shot_samples"] = few_shot_sample_count
            self.calibration_data["few_shot_similarity_threshold"] = round(few_shot_similarity_threshold, 3)
            self.calibration_data["few_shot_similarity_thresholds"] = {
                "steady": round(float(few_shot_similarity_thresholds.get("steady", few_shot_similarity_threshold)), 3),
                "right_rotation": round(float(few_shot_similarity_thresholds.get("right_rotation", few_shot_similarity_threshold)), 3),
                "left_rotation": round(float(few_shot_similarity_thresholds.get("left_rotation", few_shot_similarity_threshold)), 3),
            }
            return {
                "success": False,
                "message": f"Only {len(confidences)} detections (need {target}). Try better lighting.",
                "detections": len(confidences),
                "suggestion": "Move to a brighter area or adjust camera angle.",
            }

        avg_conf = sum(confidences) / len(confidences)  # Average quality across accepted samples.
        min_conf = min(confidences)  # Weakest accepted sample; drives the lower bound for runtime thresholding.
        max_conf = max(confidences)  # Strongest accepted sample; currently useful for reporting/debugging.

        # We anchor the live threshold near the weakest successful sample so the
        # system remains permissive enough for angled/rotating phones while still
        # enforcing a minimum floor against noisy detections.
        optimal_threshold = max(0.25, min_conf - 0.1)  # Stay slightly below the weakest good sample, but never below 0.25.

        # Lighting quality is a coarse label that can later drive UX hints or
        # extra runtime heuristics without exposing raw confidence stats alone.
        if avg_conf > 0.7:
            lighting = "excellent"
        elif avg_conf > 0.5:
            lighting = "good"
        elif avg_conf > 0.35:
            lighting = "fair"
        else:
            lighting = "poor"

        self.calibration_data = {
            "avg_confidence": round(avg_conf, 3),  # Rounded for cleaner logs/UI output.
            "min_confidence": round(min_conf, 3),  # Rounded weakest accepted confidence.
            "max_confidence": round(max_conf, 3),  # Rounded strongest accepted confidence.
            "optimal_conf_threshold": round(optimal_threshold, 2),  # Runtime threshold the app should reuse.
            "detections_count": len(confidences),  # Final count of accepted calibration samples.
            "few_shot_samples": few_shot_sample_count,  # Number of few-shot exemplars learned in Phase 1.
            "few_shot_similarity_threshold": round(few_shot_similarity_threshold, 3),  # Appearance gate learned from exemplar consistency.
            "few_shot_similarity_thresholds": {
                "steady": round(float(few_shot_similarity_thresholds.get("steady", few_shot_similarity_threshold)), 3),
                "right_rotation": round(float(few_shot_similarity_thresholds.get("right_rotation", few_shot_similarity_threshold)), 3),
                "left_rotation": round(float(few_shot_similarity_thresholds.get("left_rotation", few_shot_similarity_threshold)), 3),
            },
            "lighting_quality": lighting,  # Qualitative environment label.
            "calibrated": True,  # Signals that get_optimal_params() can trust the computed values.
        }

        # [INTELLIGENCE TEAM] 'data' contains every tuned parameter the downstream
        # runtime detector should consume. Prefer get_optimal_params() for a clean
        # dict; avoid parsing 'recommendation' string for automation.
        return {
            "success": True,
            "message": f"Calibration complete! Lighting: {lighting}",
            "data": self.calibration_data,
            "recommendation": (
                f"Use conf={optimal_threshold:.2f}; appearance gates: "
                f"S={few_shot_similarity_thresholds['steady']:.2f}, "
                f"R={few_shot_similarity_thresholds['right_rotation']:.2f}, "
                f"L={few_shot_similarity_thresholds['left_rotation']:.2f}."
            ),
        }

    def get_optimal_params(self) -> dict:
        """Return optimized detection parameters after calibration."""
        # [INTELLIGENCE TEAM] Primary interface for downstream consumers. Call this
        # after run_calibration() completes and pass the returned dict directly into
        # the phone-detection pipeline (conf, augment, few_shot gates, class filter).
        if not self.calibration_data["calibrated"]:
            return {"conf": 0.5, "augment": False}  # defaults

        conf = self.calibration_data["optimal_conf_threshold"]  # Reuse the threshold derived from accepted samples.
        
        use_augment = self.calibration_data["lighting_quality"] in ["poor", "fair"]  # Extra help only in weaker lighting conditions.

        return {
            "conf": conf,
            "augment": use_augment,
            "classes": [67],
            "few_shot_enabled": self.calibration_data.get("few_shot_samples", 0) >= 3,
            "few_shot_similarity_threshold": self.calibration_data.get("few_shot_similarity_threshold", 0.45),
            "few_shot_similarity_thresholds": self.calibration_data.get(
                "few_shot_similarity_thresholds",
                {"steady": 0.45, "right_rotation": 0.42, "left_rotation": 0.42},
            ),
        }


# Quick test
if __name__ == "__main__":
    calibrator = PhoneCalibration("yolo26n.pt")
    result = calibrator.run_calibration(target_detections=15)
    
    print("\n" + "=" * 50)
    print("CALIBRATION RESULT")
    print("=" * 50)
    for key, value in result.items():
        print(f"{key}: {value}")
    
    if result.get("success"):
        params = calibrator.get_optimal_params()
        print(f"\nOptimal parameters: {params}")