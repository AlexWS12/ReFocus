# camera.py
# Main vision module that combines phone detection and eye tracking.

from ultralytics import YOLO
import cv2 as cv
from Trackers.iris_tracker import eyeTracker


class Camera:
    """Manages webcam capture, phone detection (YOLO), and eye tracking."""

    def __init__(self, model_path="yolo26n.pt"):
        """Initialize camera, YOLO model, and eye tracker."""
        self.model = YOLO(model_path)  # Load YOLO model for object detection
        self.cap = cv.VideoCapture(0)  # Open default webcam (index 0)
        self.eye_tracker = eyeTracker()

    def read_frame(self):
        """Capture a frame, run phone detection and eye tracking.
        
        Returns:
            tuple: (original_frame, annotated_frame) or None if capture fails.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        # Detect phones only (class 67 in COCO dataset)
        results = self.model(frame, classes=[67])
        annotated = results[0].plot()  # Draw bounding boxes on frame

        # Run eye tracking on the annotated frame
        annotated = self.eye_tracker.track_eyes(annotated)

        return frame, annotated

    def release(self):
        """Release camera resources and close windows."""
        self.cap.release()
        cv.destroyAllWindows()


# This loop only runs if you click “Run” on camera.py
if __name__ == "__main__":
    cam = Camera()
    while True:
        data = cam.read_frame()
        if data is None:
            break
        _, annotated = data
        cv.imshow("Phone Detection", annotated)
        if cv.waitKey(1) == ord("q"):
            break
    cam.release()