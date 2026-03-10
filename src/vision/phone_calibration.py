import cv2
import time
from ultralytics import YOLO


class PhoneCalibration:
    def __init__(self, model_path: str = "yolo26n.pt"):
        self.model = YOLO(model_path)
        self.calibration_data = {
            "avg_confidence": 0.0,
            "optimal_conf_threshold": 0.5,
            "detections_count": 0,
            "lighting_quality": "unknown",
            "calibrated": False,
        }

    def _get_guide_box(self, frame_shape):
        """Return a centered guide box where the phone should be placed."""
        height, width = frame_shape[:2]
        box_width = int(width * 0.28)
        box_height = int(height * 0.58)
        x1 = (width - box_width) // 2
        y1 = (height - box_height) // 2
        x2 = x1 + box_width
        y2 = y1 + box_height
        return x1, y1, x2, y2

    def _draw_guide_box(self, frame, active=False):
        """Draw the phone placement guide box."""
        x1, y1, x2, y2 = self._get_guide_box(frame.shape)
        color = (0, 255, 0) if active else (0, 255, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, "Place phone inside box", (x1 - 15, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        return x1, y1, x2, y2

    def _find_phone_in_box(self, frame, conf=0.2):
        """Return the strongest phone detection and whether it is centered in the guide box."""
        results = self.model(frame, classes=[67], conf=conf, verbose=False)
        boxes = results[0].boxes
        if not boxes:
            return None, False, results

        best_box = max(boxes, key=lambda box: float(box.conf[0]))
        x1, y1, x2, y2 = map(int, best_box.xyxy[0])
        guide_x1, guide_y1, guide_x2, guide_y2 = self._get_guide_box(frame.shape)
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        in_box = guide_x1 <= center_x <= guide_x2 and guide_y1 <= center_y <= guide_y2
        return best_box, in_box, results

    def _wait_for_phone_in_box(self, cap, hold_seconds=1.5):
        """Wait until the user places the phone in the guide box steadily."""
        stable_since = None

        while True:
            ret, frame = cap.read()
            if not ret:
                return {"error": "Could not read camera frame"}

            height, width = frame.shape[:2]
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (width, 105), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

            box = self._draw_guide_box(frame, active=stable_since is not None)
            guide_x1, guide_y1, guide_x2, guide_y2 = box

            best_box, in_box, _ = self._find_phone_in_box(frame, conf=0.2)

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
                        stable_since = time.time()
                    held_for = time.time() - stable_since
                    remaining = max(0.0, hold_seconds - held_for)
                    cv2.putText(frame, f"Hold steady to start: {remaining:.1f}s", (guide_x1 - 10, guide_y2 + 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    if held_for >= hold_seconds:
                        cv2.imshow("Phone Calibration", frame)
                        cv2.waitKey(250)
                        return {"success": True}
                else:
                    stable_since = None
                    cv2.putText(frame, "Center the phone inside the box", (guide_x1 - 5, guide_y2 + 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            else:
                stable_since = None
                cv2.putText(frame, "No phone detected yet", (guide_x1 + 5, guide_y2 + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("Phone Calibration", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                return {"error": "Calibration cancelled"}

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

        confidences = []
        
        # Define calibration phases
        phases = [
            {"name": "PHASE 1", "instruction": "Hold phone steady in the box", "duration": 3, "collect": True},
            {"name": "PHASE 2", "instruction": "Rotate phone RIGHT slowly", "duration": 4, "collect": True},
            {"name": "PHASE 3", "instruction": "Rotate phone LEFT slowly", "duration": 4, "collect": True},
            {"name": "DONE", "instruction": "Processing results...", "duration": 1, "collect": False},
        ]

        for phase in phases:
            phase_start = time.time()
            
            while time.time() - phase_start < phase["duration"]:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Get frame dimensions for centering text
                h, w = frame.shape[:2]
                
                # Draw semi-transparent overlay for better text visibility
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
                self._draw_guide_box(frame)
                
                # Phase name and countdown
                remaining = int(phase["duration"] - (time.time() - phase_start)) + 1
                cv2.putText(frame, phase["name"], (10, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                cv2.putText(frame, f"{remaining}s", (w - 60, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                
                # Main instruction
                cv2.putText(frame, phase["instruction"], (10, 75),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Run detection if collecting
                if phase["collect"]:
                    best_box, in_box, results = self._find_phone_in_box(frame, conf=0.2)
                    
                    if best_box is not None:
                        conf = float(best_box.conf[0])
                        if in_box:
                            confidences.append(conf)

                        x1, y1, x2, y2 = map(int, best_box.xyxy[0])
                        color = (0, 255, 0) if in_box else (0, 165, 255)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                        status_text = f"DETECTED {conf:.0%}" if in_box else "Move phone into box"
                        cv2.putText(frame, status_text, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
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

        # Analyze results first
        result = self._analyze_calibration(confidences, target_detections)
        
        # If calibration succeeded, run validation
        if result.get("success"):
            validation = self._validate_calibration(cap)
            if validation == "retry":
                cap.release()
                cv2.destroyAllWindows()
                return self.run_calibration(target_detections)  # Retry
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
        
        conf_threshold = self.calibration_data["optimal_conf_threshold"]
        validation_duration = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < validation_duration:
            ret, frame = cap.read()
            if not ret:
                break
            
            h, w = frame.shape[:2]
            
            # Run detection with calibrated threshold
            results = self.model(frame, classes=[67], conf=conf_threshold, verbose=False)
            
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
            remaining = int(validation_duration - (time.time() - start_time))
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
        
        # Auto-accept after timeout
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

        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)

        # Set threshold slightly below minimum detected confidence
        # This ensures we catch the phone even at bad angles
        optimal_threshold = max(0.25, min_conf - 0.1)

        # Assess lighting quality
        if avg_conf > 0.7:
            lighting = "excellent"
        elif avg_conf > 0.5:
            lighting = "good"
        elif avg_conf > 0.35:
            lighting = "fair"
        else:
            lighting = "poor"

        self.calibration_data = {
            "avg_confidence": round(avg_conf, 3),
            "min_confidence": round(min_conf, 3),
            "max_confidence": round(max_conf, 3),
            "optimal_conf_threshold": round(optimal_threshold, 2),
            "detections_count": len(confidences),
            "lighting_quality": lighting,
            "calibrated": True,
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

        conf = self.calibration_data["optimal_conf_threshold"]
        
        # Use augmentation if lighting is poor or confidence variance is high
        use_augment = self.calibration_data["lighting_quality"] in ["poor", "fair"]

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