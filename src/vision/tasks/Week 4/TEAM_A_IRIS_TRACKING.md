# Team A — MediaPipe Migration & Gaze Tracking (Shah & Alex)

## Context
We're replacing the Haar cascade eye tracker with **MediaPipe Face Mesh + Iris**.  
**No training is needed** — MediaPipe ships with pre-trained models that work out of the box.  
Just `pip install mediapipe` (already in our dependencies via `uv sync`).

Team A's MediaPipe work was strong enough that the integration pass this week could focus on simplifying the gaze-detection path and making it easier to validate alongside phone detection.

---

## Phase 1: MediaPipe Setup & Basic Integration

### Install & Verify
- [x] Confirm `mediapipe` is installed (`uv sync` should handle it)
- [ ] Create a test script that initializes `mp.solutions.face_mesh` with `refine_landmarks=True`
- [ ] Run it on a webcam frame and confirm you get 478 landmarks (468 face + 10 iris)
- [ ] Print landmark count to verify iris landmarks (indices 468–477) are present

### Understand the Landmarks
- [x] Read the [MediaPipe Face Mesh docs](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) — focus on iris landmarks
- [ ] Understand what `refine_landmarks=True` does (enables iris landmark indices 468–477)
- [ ] Understand `min_detection_confidence` vs `min_tracking_confidence` — detection triggers on new faces, tracking maintains between frames
- [ ] Map out iris indices: 468 = right iris center, 469–472 = right iris ring, 473 = left iris center, 474–477 = left iris ring

### Rewrite `iris_tracker.py`
- [x] Replace the Haar cascade code with MediaPipe Face Mesh
- [x] Initialize `FaceMesh(refine_landmarks=True, max_num_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)`
- [ ] Process frames with `face_mesh.process(rgb_frame)` — remember to convert BGR → RGB
- [x] Draw iris center points using `cv2.circle()` on the frame
- [ ] Draw face mesh outline (optional — use `mp.solutions.drawing_utils`)
- [ ] Keep the same `track_eyes(frame)` method signature so `camera.py` doesn't break
- [ ] Test with the webcam — confirm iris dots track smoothly

---

## Phase 2: Parameter Tuning

### Detection Confidence
- [ ] Try `min_detection_confidence` at 0.3, 0.5, 0.7, 0.9
- [ ] Note: lower = more detections but more false positives; higher = fewer but more reliable
- [ ] Document which value works best for our use case (sitting at a desk)

### Tracking Confidence
- [ ] Try `min_tracking_confidence` at 0.3, 0.5, 0.7, 0.9
- [ ] Note how it affects frame-to-frame stability (higher = smoother but may re-detect more often)
- [ ] Document the best value for steady desk-based tracking

### Multi-Face
- [ ] Test `max_num_faces=2` — does it slow things down noticeably?
- [ ] For our app, we probably only need 1 face — document the performance difference

### Edge Cases
- [ ] Test with glasses on — does iris detection still work?
- [ ] Test at different distances (30cm, 60cm, 100cm) — note where tracking breaks
- [ ] Test in low light — how does it compare to the old Haar cascade?
- [ ] Test with face partially off-screen

---

## Phase 3: Structured Data Output

### Return Detection Data
- [ ] Change `track_eyes()` to return a data dict alongside the annotated frame
- [ ] Target format:
  ```python
  {
      "face_present": True,
      "eyes_detected": True,
      "left_iris": (x, y),       # normalized coordinates
      "right_iris": (x, y),      # normalized coordinates
      "gaze_state": "center",    # center, left, right, up, down
      "attention_confidence": 0.88
  }
  ```
- [ ] Compute `gaze_state` from iris position relative to eye corners (landmarks 33, 133 for right eye; 362, 263 for left eye)
- [ ] Compute `attention_confidence` based on how centered the iris is within the eye

### Attention States
- [ ] Define states: `ATTENTIVE`, `LOOKING_AWAY`, `EYES_CLOSED`, `FACE_NOT_VISIBLE`
- [ ] `ATTENTIVE` = face present + iris near center of eye
- [ ] `LOOKING_AWAY` = face present + iris off-center (looking left/right/up/down)
- [ ] `EYES_CLOSED` = face present + eye aspect ratio below threshold (blink detection)
- [ ] `FACE_NOT_VISIBLE` = no face detected in frame

### Smoothing
- [ ] Add temporal smoothing — don't flicker between states on single-frame glitches
- [ ] Use a rolling window (e.g., last 5 frames) to stabilize gaze state
- [ ] Only change state if new state persists for N consecutive frames

---

## Phase 4: Stretch Goals
- [ ] Blink detection using eye aspect ratio (distance between upper/lower eyelid landmarks)
- [ ] Head pose estimation from face mesh landmarks (is user leaning away?)
- [ ] Calculate time spent in each attention state (ATTENTIVE for 5m, LOOKING_AWAY for 30s, etc.)
- [ ] Explore: can we detect drowsiness from slow blink rate?

---

## Notes

### Key Differences from Week 3
| Feature | Haar (Week 3) | MediaPipe (Week 4) |
|---------|---------------|---------------------|
| Training needed | None | None |
| Output | Eye bounding boxes | 478 face landmarks + iris positions |
| Gaze direction | Not possible | Yes (iris relative to eye corners) |
| Blink detection | Not possible | Yes (eye aspect ratio) |
| Accuracy | Basic | Much better |
| Speed | Fast | Fast |

### Files to Modify
- `src/vision/Trackers/iris_tracker.py` — rewrite with MediaPipe
- `src/vision/camera.py` — may need minor updates to handle new return format
