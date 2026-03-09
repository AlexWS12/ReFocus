# Team B — Phone Detection & Open Images (Paul & Josue)

## Getting Started
- [x] Pull the `vision-team` branch
- [x] Run `uv sync` to install dependencies
- [x] Run `phone_detector.py` and confirm YOLO loads and detects objects
- [x] Run `camera.py` and confirm the webcam feed works

---

### Combine Camera with YOLO
- [x] Merge `camera.py` and `phone_detector.py` into a working live phone detector
- [x] Add `classes=[67]` to filter detections for cell phones only
- [x] Use `results[0].plot()` to draw bounding boxes on the frame
- [x] Display the annotated frame in the OpenCV window

### Experiment with Parameters
- [ ] Change `conf` threshold — try 0.25, 0.5, 0.75. Note how it affects detection accuracy *(Not documented)*
- [ ] Change `iou` threshold — try 0.3, 0.5, 0.7. Note how it handles overlapping detections *(Not documented)*
- [ ] Change `imgsz` — try 320, 640, 1280. Note the speed vs accuracy tradeoff *(Not documented)*
- [ ] Test detecting phones at different distances and angles *(Not documented)*

### Document Findings
- [ ] Note which `conf` value gives the best balance of accuracy vs false positives
- [ ] Note at what distance/angle phone detection breaks
- [ ] Share findings in the team thread

---

### Understand the Baseline
- [x] Test the pretrained COCO model on phone detection and note how well it works *(Using yolo26n.pt)*
- [ ] Try different phone angles, distances, and lighting — note where it struggles *(Not documented)*

### Improve the Dataset (Stretch Goal/ maybe for next week)
- [ ] Pick 50-100 photos of modern phones (different angles, lighting, distances)
- [ ] Label them using Roboflow or CVAT (both export to YOLO format)
- [ ] Fine-tune the pretrained model on your custom images and compare results
- [ ] Share findings in the team thread

---

## Notes

### What Was Built
YOLO phone detection integrated into `Camera` class. Uses `yolo26n.pt` model with `classes=[67]` filter for cell phones. Live detection with bounding boxes via `results[0].plot()`. Also integrated Team A's eye tracker into the same pipeline.

### Next Steps
- [ ] Experiment with `conf`, `iou`, and `imgsz` parameters
- [ ] Document detection limits (distance, angle, lighting)
- [ ] Consider fine-tuning on custom phone dataset for better accuracy

