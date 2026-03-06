# Team B — Phone Detection & Open Images (Paul & Josue)

## Getting Started
- [ ] Pull the `vision-team` branch
- [ ] Run `uv sync` to install dependencies
- [ ] Run `phone_detector.py` and confirm YOLO loads and detects objects
- [ ] Run `camera.py` and confirm the webcam feed works

---

### Combine Camera with YOLO
- [ ] Merge `camera.py` and `phone_detector.py` into a working live phone detector
- [ ] Add `classes=[67]` to filter detections for cell phones only
- [ ] Use `results[0].plot()` to draw bounding boxes on the frame
- [ ] Display the annotated frame in the OpenCV window

### Experiment with Parameters
- [ ] Change `conf` threshold — try 0.25, 0.5, 0.75. Note how it affects detection accuracy
- [ ] Change `iou` threshold — try 0.3, 0.5, 0.7. Note how it handles overlapping detections
- [ ] Change `imgsz` — try 320, 640, 1280. Note the speed vs accuracy tradeoff
- [ ] Test detecting phones at different distances and angles

### Document Findings
- [ ] Note which `conf` value gives the best balance of accuracy vs false positives
- [ ] Note at what distance/angle phone detection breaks
- [ ] Share findings in the team thread

---

### Understand the Baseline
- [ ] Test the pretrained COCO model on phone detection and note how well it works
- [ ] Try different phone angles, distances, and lighting — note where it struggles

### Improve the Dataset (Stretch Goal/ maybe for next week)
- [ ] Pick 50-100 photos of modern phones (different angles, lighting, distances)
- [ ] Label them using Roboflow or CVAT (both export to YOLO format)
- [ ] Fine-tune the pretrained model on your custom images and compare results
- [ ] Share findings in the team thread

---

## Notes
_Use this space to jot down observations:_

