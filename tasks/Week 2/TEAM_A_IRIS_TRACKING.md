# Team A — MediaPipe Iris (Shah & Alex)

## Getting Started
- [ ] Pull the `vision-team` branch
- [ ] Run `uv sync` to install dependencies
- [ ] Run `iris_tracker.py` and confirm it opens the camera and tracks your iris

## Understand the Template
- [ ] Read through `src/vision/MediaPipe/iris_tracker.py` and understand each line
- [ ] Understand what `refine_landmarks=True` does and why it's needed for iris tracking
- [ ] Understand the difference between detection confidence and tracking confidence
- [ ] Look up what iris landmark indices 468-477 represent (which points map to which part of the eye)

## Experiment with Parameters
- [ ] Change `min_detection_confidence` — try values like 0.3, 0.7, 0.9. Note how it affects face detection
- [ ] Change `min_tracking_confidence` — try values like 0.3, 0.7, 0.9. Note how it affects frame-to-frame tracking
- [ ] Change `max_num_faces` — try 2 or 3, test with multiple people on camera
- [ ] Test at different distances from the camera and note when tracking breaks

## Explore Iris Landmarks
- [ ] Print all iris landmarks (468-477) and understand what each one represents
- [ ] Try drawing circles on the iris center points using `cv2.circle()`
- [ ] Calculate the distance between left and right iris — what could this tell us?
- [ ] Explore: can you determine gaze direction from iris position relative to eye corners?

## Document Findings
- [ ] Note which confidence values work best for reliable tracking
- [ ] Note any limitations (lighting, distance, angles, glasses, etc.)
- [ ] Share findings in the team thread

## Stretch Goals (Maybe for next week)
- [ ] Detect if the user is looking at the screen vs looking away (gaze estimation)
- [ ] Track blink detection using the eye aspect ratio (distance between upper/lower eyelid landmarks)
- [ ] Explore: could we use iris tracking to determine how long someone has been focused?
- [ ] Try combining iris tracking with the camera feed from `camera.py`

## Notes
_Use this space to jot down observations:_

