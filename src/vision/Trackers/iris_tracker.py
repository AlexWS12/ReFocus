# iris_tracker.py
# Eye tracking using OpenCV Haar cascades.

import cv2 as cv


class eyeTracker:
    """Detects faces and eyes using Haar cascade classifiers."""

    def __init__(self):
        """Load pre-trained Haar cascades for face and eye detection."""
        self.face_cascade = cv.CascadeClassifier(
            cv.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv.CascadeClassifier(
            cv.data.haarcascades + "haarcascade_eye.xml"
        )

    def track_eyes(self, frame):
        """Detect faces and eyes in a frame, draw bounding boxes.
        
        Args:
            frame: BGR image from OpenCV.
            
        Returns:
            frame: Annotated frame with face (blue) and eye (green) boxes.
        """
        # Convert to grayscale for cascade detection
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        
        # Detect faces (scaleFactor=1.3, minNeighbors=6)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 6)

        for (x, y, w, h) in faces:
            # Draw blue rectangle around face
            cv.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            # Search for eyes only in upper half of face (where eyes are)
            roi_gray = gray[y : y + h//2, x : x + w]
            roi_color = frame[y : y + h//2, x : x + w]

            # Detect eyes within the face ROI
            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 8)
            for (ex, ey, ew, eh) in eyes:
                # Draw green rectangle around each eye
                cv.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

        return frame