# Team A Recommendations: Face / Eye / Iris Tracking

## Goal
Team A should focus on building a modular attention-tracking pipeline rather than only drawing eye boxes on the webcam feed.

## Main Recommendation
The final tracker should output usable attention signals for the app, such as:
- face_present
- eyes_detected
- iris_detected
- gaze_state
- attention_confidence
- look_away_duration
- tracking_lost

## Suggested Architecture
Recommended modular files:
- camera.py -> shared webcam input only
- face_tracker.py -> face detection / face landmarks
- iris_tracker.py -> eye + iris tracking
- attention_monitor.py -> converts detections into attention states
- vision_events.py -> event/state outputs for UI and analytics

## Important Design Notes
1. Keep camera logic separate from tracking logic.
2. Face detection should happen before eye/iris tracking.
3. The tracker should return structured data, not just an annotated frame.
4. Avoid using a single bad frame to mark distraction.
5. Use smoothing and short time thresholds to reduce flickering.
6. If face tracking is suddenly lost while a phone is detected, treat that as a meaningful event.

## Short-Term Implementation
A Haar-based eye detector can be used as a temporary prototype, but the better long-term solution is:
- MediaPipe Face Mesh
- MediaPipe Iris
- OpenCV for camera input and debug overlays

## Suggested Attention States
- ATTENTIVE
- BRIEF_GLANCE_AWAY
- LOOKING_AWAY
- FACE_NOT_VISIBLE
- TRACKING_UNCERTAIN

## Why This Matters
The rest of the app will need stable distraction signals, not just bounding boxes. A modular attention-tracking design will be easier to integrate with the UI, analytics, and future improvements.
