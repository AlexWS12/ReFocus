import cv2 as cv
import mediapipe as mp
import numpy as np
import time

from Trackers.attention_tracker import gazeTracker


class GazeCalibrator:
    """Calibrates neutral center and screen-corner gaze envelope."""

    def __init__(self, samples_per_target: int = 20):
        self.samples_per_target = samples_per_target
        self.tracker = gazeTracker()

    def _target_position(self, target_name: str, w: int, h: int) -> tuple[int, int]:
        # [UX/UI TEAM] 12 % margin keeps targets away from bezels and taskbars
        # where users cannot comfortably look without rotating their head.
        # [INTELLIGENCE TEAM] These pixel positions define the spatial anchors for
        # yaw/pitch bounds; changing the margin directly affects envelope coverage.
        margin_x = int(w * 0.12)
        margin_y = int(h * 0.12)
        if target_name == "center":
            return (w // 2, h // 2)
        if target_name == "top_left":
            return (margin_x, margin_y)
        if target_name == "top_right":
            return (w - margin_x, margin_y)
        if target_name == "bottom_left":
            return (margin_x, h - margin_y)
        return (w - margin_x, h - margin_y)

    def _draw_target(self, frame, target_name: str):
        # [UX/UI TEAM] A crosshair (two lines) rather than a filled circle minimises
        # occlusion of the exact pixel the user needs to fixate on.
        h, w = frame.shape[:2]
        tx, ty = self._target_position(target_name, w, h)
        cv.line(frame, (tx - 16, ty), (tx + 16, ty), (0, 255, 255), 2)
        cv.line(frame, (tx, ty - 16), (tx, ty + 16), (0, 255, 255), 2)

    def run(self) -> dict:
        """Guide the user through center + corner targets and persist a calibration profile."""
        cap = cv.VideoCapture(0)
        if not cap.isOpened():
            return {"success": False, "message": "Cannot open camera"}

        targets = ["center", "top_left", "top_right", "bottom_left", "bottom_right"]
        labels = {
            "center": "CENTER",
            "top_left": "TOP LEFT",
            "top_right": "TOP RIGHT",
            "bottom_left": "BOTTOM LEFT",
            "bottom_right": "BOTTOM RIGHT",
        }
        samples = {name: {"yaw": [], "pitch": [], "roll": []} for name in targets}

        target_index = 0
        last_detection_ts = 0.0
        detection_interval = 0.12  # Sample at ~8 Hz; faster than this yields highly correlated samples.

        while target_index < len(targets):
            ok, frame = cap.read()
            if not ok:
                cap.release()
                cv.destroyAllWindows()
                return {"success": False, "message": "Could not read camera frame"}

            h, w = frame.shape[:2]
            current_target = targets[target_index]
            bucket = samples[current_target]

            self._draw_target(frame, current_target)
            cv.putText(frame, "GAZE CALIBRATION (CENTER + CORNERS)", (20, 35), cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv.putText(
                frame,
                f"Look at: {labels[current_target]}",
                (20, 68),
                cv.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )
            cv.putText(
                frame,
                "Press [N] next target  [R] reset target  [Q] cancel",
                (20, 98),
                cv.FONT_HERSHEY_SIMPLEX,
                0.55,
                (200, 200, 200),
                1,
            )

            now = time.monotonic()
            if now - last_detection_ts >= detection_interval and len(bucket["yaw"]) < self.samples_per_target:
                rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = self.tracker.detector.detect(mp_image)
                landmarks = result.face_landmarks[0] if result.face_landmarks else None

                if landmarks is not None:
                    pitch, yaw, roll, _, _, _, _ = self.tracker.estimate_head_pose(landmarks, frame)
                    # [INTELLIGENCE TEAM] Raw head-pose angles in degrees, stored per target.
                    # Center-subtracted versions of these become the gaze envelope bounds.
                    bucket["yaw"].append(float(yaw))
                    bucket["pitch"].append(float(pitch))
                    bucket["roll"].append(float(roll))
                    cv.putText(frame, "Face detected - sampling...", (20, h - 44), cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
                else:
                    cv.putText(frame, "No face detected.", (20, h - 44), cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

                last_detection_ts = now

            # [UX/UI TEAM] Live sample counter acts as a progress bar so users know
            # exactly how many samples are needed before they can press [N] to advance.
            cv.putText(
                frame,
                f"Target samples: {len(bucket['yaw'])}/{self.samples_per_target}",
                (20, h - 14),
                cv.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 0),
                2,
            )

            cv.imshow("Gaze Calibration", frame)
            key = cv.waitKey(1) & 0xFF

            # [UX/UI TEAM] Always allow immediate escape so users cannot get stuck.
            if key == ord("q"):
                cap.release()
                cv.destroyAllWindows()
                return {"success": False, "message": "Gaze calibration cancelled"}

            if key == ord("r"):
                bucket["yaw"].clear()
                bucket["pitch"].clear()
                bucket["roll"].clear()

            auto_complete = len(bucket["yaw"]) >= self.samples_per_target
            # Allow early advance only when at least 1/3 of the target samples are collected
            # (minimum 6) so the user cannot skip a target before any useful data is gathered.
            manual_next = key == ord("n") and len(bucket["yaw"]) >= max(6, self.samples_per_target // 3)
            if auto_complete or manual_next:
                target_index += 1

        cap.release()
        cv.destroyAllWindows()

        # [INTELLIGENCE TEAM] Median is used instead of mean to suppress blink-related
        # pose spikes that occasionally contaminate the center-target sample window.
        center_yaw = float(np.median(np.array(samples["center"]["yaw"], dtype=np.float64)))
        center_pitch = float(np.median(np.array(samples["center"]["pitch"], dtype=np.float64)))
        center_roll = float(np.median(np.array(samples["center"]["roll"], dtype=np.float64)))

        # [INTELLIGENCE TEAM] All corner samples are expressed relative to the center
        # offset, not as absolute angles. This makes the envelope user-specific and
        # independent of the user's natural resting head posture.
        corrected_yaw = []
        corrected_pitch = []
        corrected_roll = []
        for name in targets:
            yaws = np.array(samples[name]["yaw"], dtype=np.float64) - center_yaw
            pitches = np.array(samples[name]["pitch"], dtype=np.float64) - center_pitch
            rolls = np.array(samples[name]["roll"], dtype=np.float64) - center_roll
            corrected_yaw.extend(yaws.tolist())
            corrected_pitch.extend(pitches.tolist())
            corrected_roll.extend(rolls.tolist())

        # Small expansion helps avoid false "away" on micro-movements.
        margin_deg = 2.0
        # [INTELLIGENCE TEAM] yaw_min/yaw_max and pitch_min/pitch_max form the
        # "on-screen gaze" envelope. Any pose outside this box is classified as
        # gaze-away. roll_threshold is a separate head-tilt guard computed below.
        yaw_min = float(min(corrected_yaw) - margin_deg)
        yaw_max = float(max(corrected_yaw) + margin_deg)
        pitch_min = float(min(corrected_pitch) - margin_deg)
        pitch_max = float(max(corrected_pitch) + margin_deg)
        # Roll threshold: 95th percentile of absolute corrected roll across all targets,
        # plus a 3° buffer, with a hard floor of 12° to avoid false "away" on minor tilts.
        # Using the 95th percentile instead of the max suppresses occasional pose spikes.
        roll_threshold = float(max(12.0, np.percentile(np.abs(np.array(corrected_roll, dtype=np.float64)), 95) + 3.0))

        # [INTELLIGENCE TEAM] The profile dict is the calibration contract between
        # the data-collection phase and the runtime attention tracker. version=2
        # indicates the center-offset + corner-envelope schema. Pass this to
        # tracker.set_calibration_profile() to activate it in the live pipeline.
        profile = {
            "version": 2,
            "center_offsets": {
                "yaw_deg": center_yaw,
                "pitch_deg": center_pitch,
                "roll_deg": center_roll,
            },
            "yaw_bounds": {"min": yaw_min, "max": yaw_max},
            "pitch_bounds": {"min": pitch_min, "max": pitch_max},
            "roll_threshold_deg": roll_threshold,
            "samples_per_target": self.samples_per_target,
            "targets": targets,
            "updated_at": int(time.time()),
        }

        self.tracker.set_calibration_profile(profile)

        return {
            "success": True,
            "message": "Gaze calibration saved (center + corners)",
            "yaw_center_deg": center_yaw,
            "pitch_center_deg": center_pitch,
            "roll_center_deg": center_roll,
            "yaw_bounds": profile["yaw_bounds"],
            "pitch_bounds": profile["pitch_bounds"],
            "roll_threshold_deg": profile["roll_threshold_deg"],
            "calibration_file": self.tracker.calibration_file,
        }


if __name__ == "__main__":
    calibrator = GazeCalibrator()
    print(calibrator.run())
