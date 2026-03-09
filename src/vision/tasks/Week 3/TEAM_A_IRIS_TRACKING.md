# Team A — MediaPipe Iris (Shah & Alex)

## Getting Started
- [x] Pull the `vision-team` branch
- [x] Run `uv sync` to install dependencies
- [x] Run `iris_tracker.py` and confirm it opens the camera and tracks your iris

## Understand the Template
- [x] Read through `src/vision/MediaPipe/iris_tracker.py` and understand each line
- [ ] Understand what `refine_landmarks=True` does and why it's needed for iris tracking *(Not done — used Haar cascades instead)*
- [ ] Understand the difference between detection confidence and tracking confidence *(Not done — MediaPipe not used yet)*
- [ ] Look up what iris landmark indices 468-477 represent (which points map to which part of the eye) *(Not done — MediaPipe not used yet)*

## Experiment with Parameters
- [x] Change `min_detection_confidence` — try values like 0.3, 0.7, 0.9. Note how it affects face detection *(Used Haar cascade scaleFactor=1.3, minNeighbors=6)*
- [ ] Change `min_tracking_confidence` — try values like 0.3, 0.7, 0.9. Note how it affects frame-to-frame tracking *(Not applicable — Haar cascades don't have tracking confidence)*
- [ ] Change `max_num_faces` — try 2 or 3, test with multiple people on camera *(Not tested)*
- [ ] Test at different distances from the camera and note when tracking breaks *(Not documented)*

## Explore Iris Landmarks
- [ ] Print all iris landmarks (468-477) and understand what each one represents *(Not done — MediaPipe not used yet)*
- [x] Try drawing circles on the iris center points using `cv2.circle()` *(Used cv2.rectangle for eye regions instead)*
- [ ] Calculate the distance between left and right iris — what could this tell us? *(Not done)*
- [ ] Explore: can you determine gaze direction from iris position relative to eye corners? *(Not done)*

## Document Findings
- [x] Note which confidence values work best for reliable tracking *(Documented in team_a_recommendations.md)*
- [x] Note any limitations (lighting, distance, angles, glasses, etc.) *(Documented in team_a_recommendations.md)*
- [x] Share findings in the team thread *(Created branch plan and recommendations)*

## Stretch Goals (Maybe for next week)
- [ ] Detect if the user is looking at the screen vs looking away (gaze estimation)
- [ ] Track blink detection using the eye aspect ratio (distance between upper/lower eyelid landmarks)
- [ ] Explore: could we use iris tracking to determine how long someone has been focused?
- [x] Try combining iris tracking with the camera feed from `camera.py` *(Integrated eyeTracker into Camera class)*

## Notes

### What Was Built
Haar cascade-based `eyeTracker` class using OpenCV for face/eye detection. Integrated into `camera.py`. Returns annotated frames with rectangles (face=blue, eyes=green). Should upgrade to MediaPipe for better accuracy.

### Next Steps
- [ ] Return structured detection data (not just annotated frames)
- [ ] Add smoothing/stability logic to reduce flickering  
- [ ] Define attention states: ATTENTIVE, LOOKING_AWAY, FACE_NOT_VISIBLE, etc.
- [ ] Add comments and usage notes

### Target Output Format
```python
{"face_present": True, "eyes_detected": True, "gaze_state": "center", "attention_confidence": 0.88, "state": "ATTENTIVE"}
```

### Architecture Recommendation
Keep camera separate from tracking. Modular files: `camera.py` → `iris_tracker.py` → `attention_monitor.py` → `vision_events.py`

