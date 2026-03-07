import cv2 as cv

class eyeTracker:
    def __init__(self):
        self.face_cascade = cv.CascadeClassifier(
            cv.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv.CascadeClassifier(
            cv.data.haarcascades + "haarcascade_eye.xml"
        )

    def track_eyes(self, frame):
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 6)

        for (x, y, w, h) in faces:
            cv.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            roi_gray = gray[y : y + h//2, x : x + w]
            roi_color = frame[y : y + h//2, x : x + w]

            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 8)
            for (ex, ey, ew, eh) in eyes:
                cv.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

        # cv.imshow("Eye Tracker", frame)  # Optional: remove for modular use
        return frame