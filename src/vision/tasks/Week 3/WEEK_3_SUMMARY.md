# Vision Team — Week 3 Summary

## Overview
Both teams completed their core integration tasks. The vision pipeline now has live phone detection and eye tracking working together in `camera.py`.

---

## Team A — Eye/Iris Tracking (Shah & Alex)

**Completed:**
- Built `gazeTracker` class using OpenCV Haar cascades
- Face detection (blue rectangles) + eye detection (green rectangles)
- Integrated into `camera.py` alongside phone detection
- Created architecture recommendations for attention monitoring

**Not Completed:**
- MediaPipe integration (used Haar cascades as prototype instead)
- Structured data output (currently returns annotated frames only)
- Parameter experimentation documentation

**Next Steps:**
- Return structured detection data: `{face_present, eyes_detected, gaze_state, attention_confidence}`
- Add smoothing logic to reduce flickering
- Define attention states (ATTENTIVE, LOOKING_AWAY, etc.)

---

## Team B — Phone Detection (Paul & Josue)

**Completed:**
- YOLO phone detection integrated into `Camera` class
- Using `yolo26n.pt` model with `classes=[67]` filter for cell phones
- Live bounding box visualization with `results[0].plot()`
- Combined with Team A's eye tracker in unified pipeline

**Not Completed:**
- Parameter experimentation (`conf`, `iou`, `imgsz`)
- Documentation of detection limits (distance, angle, lighting)

**Next Steps:**
- Experiment with confidence/IOU thresholds for optimal accuracy
- Document where detection breaks down
- Consider fine-tuning on custom phone dataset

---

## Current State

The `camera.py` file now runs both detections in a single loop:
1. YOLO detects phones → draws bounding boxes
2. Haar cascades detect face/eyes → draws rectangles
3. Combined annotated frame displayed in OpenCV window

**Run with:** `python src/vision/camera.py` (press 'q' to quit)

---

## Week 4 Priorities
1. **Team A:** Upgrade to MediaPipe Face Mesh + Iris for better tracking accuracy
2. **Team A:** Return structured attention signals instead of just annotated frames
3. **Team B:** Document optimal YOLO parameters
4. **Both:** Add event system to communicate detections to UI/analytics
