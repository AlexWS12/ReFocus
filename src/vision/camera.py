# camera.py
from ultralytics import YOLO
import cv2 as cv
from MediaPipe.iris_tracker import eyeTracker

class Camera:
    def __init__(self, model_path="yolo26n.pt"):
        self.model = YOLO(model_path)
        self.cap = cv.VideoCapture(0)
        self.eye_tracker = eyeTracker()

    def read_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None

        results = self.model(frame, classes=[67])  # phones only
        annotated = results[0].plot()

        # Run eye tracking on the annotated frame
        annotated = self.eye_tracker.track_eyes(annotated)

        return frame, annotated

    def release(self):
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