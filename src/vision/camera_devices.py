# Enumerate available video capture devices via OpenCV

import cv2 as cv


def list_cameras(max_index: int = 8) -> list[dict]:
    # Probe camera indices 0..max_index-1 and return those that open
    cameras: list[dict] = []
    for idx in range(max_index):
        cap = cv.VideoCapture(idx)
        if cap.isOpened():
            cameras.append({"index": idx, "name": f"Camera {idx}"})
            cap.release()
    return cameras
