# camera.py
# Main vision module that combines phone detection and eye tracking.

from ultralytics import YOLO
import cv2 as cv
from Trackers.iris_tracker import eyeTracker
from phone_calibration import PhoneCalibration


class Camera:
    """Manages webcam capture, phone detection (YOLO), and eye tracking."""

    def __init__(self, model_path="yolo26n.pt"):
        """Initialize camera, YOLO model, and eye tracker."""
        self.model = YOLO(model_path)  # Load YOLO model for object detection
        self.cap = cv.VideoCapture(0)  # Open default webcam (index 0)
        self.eye_tracker = eyeTracker()
        self.detection_params = {"conf": 0.35}  # Default parameters

    def calibrate(self) -> bool:
        """Run interactive calibration before starting detection."""
        calibrator = PhoneCalibration()
        result = calibrator.run_calibration()  # Uses new multi-phase flow
        
        if result.get("success"):
            self.detection_params = calibrator.get_optimal_params()
            print(f"Using params: {self.detection_params}")
            return True
        else:
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
        results = self.model(frame, classes=[67], conf=self.detection_params.get("conf", 0.35), iou=0.3, imgsz=640)  # Adjust confidence, IoU, and image size as needed
        annotated = results[0].plot()  # Draw bounding boxes on frame

        # Run eye tracking on the annotated frame
        annotated = self.eye_tracker.track_eyes(annotated)

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