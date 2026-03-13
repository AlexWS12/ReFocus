import cv2
import math
import numpy as np
import time
from ultralytics import YOLO


class PhoneCalibration:
    """Interactive helper that tunes phone-detection settings for the current user/environment."""

    def __init__(self, model_path: str = "yolo26n.pt"):
        self.model = YOLO(model_path)  # Load the base detector once and reuse it for all calibration steps.
        self.calibration_data = {
            "avg_confidence": 0.0,  # Mean confidence across accepted calibration samples.
            "optimal_conf_threshold": 0.5,  # Default fallback until calibration computes a better threshold.
            "detections_count": 0,  # Number of accepted samples collected during calibration.
            "lighting_quality": "unknown",  # Qualitative label derived from average confidence.
            "calibrated": False,  # Flips to True only after enough usable samples are collected.
        }

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
        x1, y1, x2, y2 = self._get_guide_box(frame.shape)
        color = (0, 255, 0) if active else (0, 255, 255)  # Green = locked in, yellow = waiting for alignment.
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)  # Draw the actual placement target.
        cv2.putText(frame, "Place phone inside box", (x1 - 15, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        return x1, y1, x2, y2

    def _find_phone_in_box(self, frame, conf=0.2):
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

    def _draw_rotation_arrow(self, frame, direction: str, guide_box: tuple):
        """Draw a smooth anti-aliased arc arrow using Pillow."""
        from PIL import Image, ImageDraw
        h, w = frame.shape[:2]
        gx1, gy1, gx2, gy2 = guide_box
        guide_cy = (gy1 + gy2) // 2
        R = 52
        color_rgb = (255, 200, 0)   # warm yellow — RGB for PIL
        color_bgr = (0, 200, 255)   # same color — BGR for cv2 label text

        # Convert BGR frame to RGB PIL image so Pillow can draw anti-aliased shapes.
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        if direction == "right":
            cx = min(gx2 + R + 15, w - R - 5)  # place arc to the right of the guide box
            arc_start, arc_end = 240, 120        # ¾ C opening left; PIL wraps clockwise past 360
            tip_ang = math.radians(120)          # angle (screen-clockwise from 3-o'clock) of the arc endpoint
            label = "ROTATE RIGHT"
        else:
            cx = max(gx1 - R - 15, R + 5)       # place arc to the left of the guide box
            arc_start, arc_end = 60, 300         # ¾ C opening right
            tip_ang = math.radians(300)
            label = "ROTATE LEFT"

        # Anti-aliased arc — cv2.ellipse does not support LINE_AA for thick arcs.
        bbox = [cx - R, guide_cy - R, cx + R, guide_cy + R]
        draw.arc(bbox, start=arc_start, end=arc_end, fill=color_rgb, width=5)

        # Filled arrowhead triangle at the arc endpoint.
        # Clockwise tangent vector in screen coords at angle θ: (-sin θ, cos θ).
        tx, ty   = math.cos(tip_ang), math.sin(tip_ang)  # unit radius vector at tip
        tant_x   = -ty                                    # clockwise tangent x = -sin(tip_ang)
        tant_y   =  tx                                    # clockwise tangent y =  cos(tip_ang)
        perp_x, perp_y = tant_y, -tant_x                 # perpendicular (radial direction) for base width

        tip_x = cx + R * tx
        tip_y = guide_cy + R * ty
        arr = 14  # arrowhead length in pixels
        apex   = (tip_x + arr * tant_x,           tip_y + arr * tant_y)
        base_l = (tip_x + arr * 0.45 * perp_x,    tip_y + arr * 0.45 * perp_y)
        base_r = (tip_x - arr * 0.45 * perp_x,    tip_y - arr * 0.45 * perp_y)
        draw.polygon([apex, base_l, base_r], fill=color_rgb)

        # Write Pillow changes back into the OpenCV BGR frame in-place.
        frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

        # Label via cv2 with LINE_AA — PIL's built-in font is too pixelated at small sizes.
        label_x = cx - 55
        label_y = min(guide_cy + R + 22, h - 8)
        cv2.putText(frame, label, (label_x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2, cv2.LINE_AA)

    def _wait_for_phone_in_box(self, cap, hold_seconds=1.5):
        """Wait until the user places the phone in the guide box steadily."""
        stable_since = None  # Timestamp marking when the phone first became valid and centered.

        while True:
            ret, frame = cap.read()
            if not ret:
                return {"error": "Could not read camera frame"}

            height, width = frame.shape[:2]
            overlay = frame.copy()  # Draw overlays on a copy first so text remains readable.
            cv2.rectangle(overlay, (0, 0), (width, 105), (0, 0, 0), -1)  # Dark banner behind top instructions.
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)  # Blend overlay back onto the live frame.

            box = self._draw_guide_box(frame, active=stable_since is not None)
            guide_x1, guide_y1, guide_x2, guide_y2 = box

            best_box, in_box, _ = self._find_phone_in_box(frame, conf=0.2)  # Use low threshold during setup to avoid missing borderline poses.

            cv2.putText(frame, "CALIBRATION READY", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            cv2.putText(frame, "Place your phone inside the box to begin", (10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Press Q to cancel", (10, 95),
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

    def _prompt_retry_or_quit(self, cap, phase_name: str) -> str:
        """
        Freeze the feed and show a timeout screen.
        Returns 'retry' to redo the current phase, or 'quit' to abort.
        """
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

        # Validation-first phases: each phase advances when enough valid frames are seen.
        # A timeout still exists so the user can retry instead of being stuck forever.
        phases = [
            {
                "name": "PHASE 1",
                "instruction": "Hold phone steady in the box",
                "required_valid_frames": 12,  # Lowered from 18 — fewer steady frames needed to baseline.
                "max_seconds": 20,
                "kind": "steady",
                "collect": True,
            },
            {
                "name": "PHASE 2",
                "instruction": "Rotate phone RIGHT about 90 degrees",
                "required_valid_frames": 7,  # Lowered from 10 — easier to hit with relaxed thresholds.
                "max_seconds": 25,
                "kind": "right_rotation",
                "collect": True,
            },
            {
                "name": "PHASE 3",
                "instruction": "Rotate phone LEFT about 90 degrees",
                "required_valid_frames": 7,  # Lowered from 10.
                "max_seconds": 25,
                "kind": "left_rotation",
                "collect": True,
            },
        ]

        for phase in phases:
            phase_start = time.time()
            valid_frames = 0
            phase_start_x = None

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

                # Draw directional arc arrow for rotation phases so the user knows which way to turn.
                if phase["kind"] in ("right_rotation", "left_rotation"):
                    direction = "right" if phase["kind"] == "right_rotation" else "left"
                    self._draw_rotation_arrow(frame, direction, guide_box)

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
                
                # Run detection if collecting
                if phase["collect"]:
                    best_box, in_box, _ = self._find_phone_in_box(frame, conf=0.2)
                    
                    if best_box is not None:
                        conf = float(best_box.conf[0])
                        metrics = self._box_metrics(best_box, frame.shape)

                        if phase_start_x is None:
                            phase_start_x = metrics["center_x_norm"]

                        is_valid = False

                        if phase["kind"] == "steady":
                            # "Steady" means centered and still mostly upright.
                            is_valid = in_box and metrics["aspect_ratio"] >= 1.2
                            if is_valid:
                                baseline_metrics.append(metrics)

                        elif phase["kind"] == "right_rotation" and baseline is not None:
                            is_valid = in_box and self._rotation_valid(metrics, baseline, "right", phase_start_x)

                        elif phase["kind"] == "left_rotation" and baseline is not None:
                            is_valid = in_box and self._rotation_valid(metrics, baseline, "left", phase_start_x)

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
                    else:
                        # Red text when not detected
                        cv2.putText(frame, "No phone detected - place it inside the box", (10, h - 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Show running detection count
                cv2.putText(frame, f"Samples: {len(confidences)}", (w - 150, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                cv2.imshow("Phone Calibration", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return {"error": "Calibration cancelled"}

                # Move on only when validation requirements are met.
                if valid_frames >= phase["required_valid_frames"]:
                    if phase["kind"] == "steady" and baseline_metrics:
                        count = len(baseline_metrics)
                        baseline = {
                            "width_norm": sum(m["width_norm"] for m in baseline_metrics) / count,
                            "area_ratio": sum(m["area_ratio"] for m in baseline_metrics) / count,
                        }
                    break

                # On timeout, pause and let the user choose to retry the phase or quit.
                if elapsed >= phase["max_seconds"]:
                    choice = self._prompt_retry_or_quit(cap, phase["name"])
                    if choice == "retry":
                        # Reset phase state and try again without restarting the whole flow.
                        phase_start = time.time()
                        valid_frames = 0
                        phase_start_x = None
                        if phase["kind"] == "steady":
                            baseline_metrics.clear()  # Discard stale baseline samples before re-collecting.
                        continue
                    else:
                        cap.release()
                        cv2.destroyAllWindows()
                        return {
                            "success": False,
                            "message": f"{phase['name']} validation failed.",
                            "suggestion": "Re-run calibration and rotate farther while keeping phone inside the box.",
                        }

        # Analyze results first
        result = self._analyze_calibration(confidences, target_detections)  # Convert raw sample confidences into runtime settings.
        
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
        
        cap.release()
        cv2.destroyAllWindows()

        return result
    
    def _validate_calibration(self, cap) -> str:
        """
        Let user verify detection is working with calibrated parameters.
        Returns: 'accept', 'retry', or 'cancel'
        """
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

    def _analyze_calibration(self, confidences: list, target: int) -> dict:
        """Analyze collected data and set optimal parameters."""
        
        if len(confidences) < target:
            self.calibration_data["calibrated"] = False
            self.calibration_data["lighting_quality"] = "poor"
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
            "lighting_quality": lighting,  # Qualitative environment label.
            "calibrated": True,  # Signals that get_optimal_params() can trust the computed values.
        }

        return {
            "success": True,
            "message": f"Calibration complete! Lighting: {lighting}",
            "data": self.calibration_data,
            "recommendation": f"Use conf={optimal_threshold:.2f} for best results.",
        }

    def get_optimal_params(self) -> dict:
        """Return optimized detection parameters after calibration."""
        if not self.calibration_data["calibrated"]:
            return {"conf": 0.5, "augment": False}  # defaults

        conf = self.calibration_data["optimal_conf_threshold"]  # Reuse the threshold derived from accepted samples.
        
        use_augment = self.calibration_data["lighting_quality"] in ["poor", "fair"]  # Extra help only in weaker lighting conditions.

        return {
            "conf": conf,
            "augment": use_augment,
            "classes": [67],
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