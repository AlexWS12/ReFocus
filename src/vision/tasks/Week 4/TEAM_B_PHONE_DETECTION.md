# Team B — YOLO Optimization & Detection Events (Paul & Josue)

## Context
Phone detection is working with `yolo26n.pt` and `classes=[67]`. The latest push also added an **interactive calibration flow** that guides the user to place the phone in a box, rotate it, and derive a better confidence threshold before live detection starts. This week the priority is to **improve detection reliability without new model training**: validate defaults, harden calibration, document detection limits, and output structured detection data the rest of the app can use.

This week also included collaboration with the team lead on calibration UX, animated rotation guidance, test-menu shortcuts, and few-shot appearance learning to improve detection across user-specific phone views.

---

## Phase 1: Parameter Experimentation

### Confidence Threshold (`conf`)
- [ ] Run detection with `conf=0.25` — count false positives over 1 minute of video
- [ ] Run detection with `conf=0.50` — same test, compare
- [ ] Run detection with `conf=0.75` — same test, compare
- [ ] Document: which value gives the best balance of catching phones vs avoiding false positives?
- [ ] Test with phone face-down, face-up, and at an angle — does `conf` affect which orientations are caught?

### IOU Threshold (`iou`)
- [ ] Test `iou=0.3` — note how it handles overlapping detections
- [ ] Test `iou=0.5` — compare
- [ ] Test `iou=0.7` — compare
- [ ] Document: when do overlapping boxes become a problem? (probably only with multiple phones)

### Image Size (`imgsz`)
- [ ] Test `imgsz=320` — note FPS and detection accuracy
- [ ] Test `imgsz=640` — compare (this is the default)
- [ ] Test `imgsz=1280` — compare
- [ ] Document the speed vs accuracy tradeoff — which is best for real-time webcam?

### Recommended Values
- [ ] Write up the recommended combination of `conf`, `iou`, and `imgsz` for our use case
- [ ] Validate the current baseline in `camera.py` (`conf` from calibration/default `0.35`, `iou=0.3`, `imgsz=640`) and update if experiments show better values

---

## Phase 2: Detection Limits

### Distance Testing
- [ ] Test phone detection at ~30cm from camera — document result
- [ ] Test at ~60cm — document
- [ ] Test at ~100cm — document
- [ ] Test at ~150cm+ — document where detection breaks
- [ ] Note: what's the minimum/maximum reliable distance?

### Angle Testing
- [ ] Test phone held straight-on (facing camera)
- [ ] Test phone at 45° angle
- [ ] Test phone at 90° (edge-on) — can YOLO still detect it?
- [ ] Test phone held behind/beside the user (partially visible)

### Lighting & Environment
- [ ] Test in well-lit room
- [ ] Test in dim lighting
- [ ] Test with backlight (window behind user)
- [ ] Does phone screen being on/off affect detection?

### Object Confusion
- [ ] Test with similar objects: tablet, TV remote, calculator, book
- [ ] Document any false positives with non-phone objects
- [ ] If false positives are common, note which objects trigger them

---

## Phase 3: Structured Detection Output

### Return Detection Data
- [ ] Add a method or update `read_frame()` to return structured data alongside the annotated frame
- [ ] Target format:
  ```python
  {
      "phone_detected": True,
      "phone_count": 1,
      "detections": [
          {
              "confidence": 0.87,
              "bbox": (x1, y1, x2, y2),  # bounding box coordinates
              "area_ratio": 0.05          # how much of frame the phone occupies
          }
      ]
  }
  ```
- [ ] Calculate `area_ratio` = (bbox area) / (frame area) — useful for knowing if phone is close vs far

### Detection Events
- [ ] Define events: `PHONE_APPEARED`, `PHONE_STILL_PRESENT`, `PHONE_GONE`
- [ ] Track phone presence across frames — don't fire `PHONE_APPEARED` every single frame
- [ ] Add a cooldown: only fire `PHONE_GONE` if phone has been absent for N frames (avoid flicker)
- [ ] Add timestamp to events for logging

---

## Phase 4: Calibration Hardening & Detection Robustness

**Why:** Everyone's phone case is different. Before spending time on datasets or custom training, we should push the base model and calibration flow as far as they can go. Better thresholds, better sampling, and clearer calibration UX may solve most of the real-world misses without adding training complexity.

### Data Collection Pipeline
- [x] Build an interactive calibration flow that prompts the user to place their phone in a guide box and rotate it for sampling
- [x] Add a calibration test GUI so the flow can be run without launching the full app
- [x] Hook calibration into `Camera` so live detection can use calibrated parameters
- [x] Analyze collected detections to derive a recommended confidence threshold and lighting quality result
- [x] Add a validation step so the user can accept, retry, or cancel calibration results
- [ ] Persist calibration results per user instead of keeping them in memory for the current run only
- [ ] Save calibration metadata per user (threshold, lighting quality, sample count, timestamp)
- [ ] Reuse saved calibration settings automatically on the next launch
- [ ] Add a clear re-calibrate option if detection quality drops or the user changes phone/case
- [ ] Integrate calibration into a real first-run / re-calibration user flow in the app

### Calibration Improvements
- [ ] Test whether multiple calibration passes improve results more than a single pass
- [ ] Compare short vs longer calibration sessions (for example 10 vs 20+ samples)
- [x] Add clearer animated prompts for rotation guidance so calibration is easier to follow
- [x] Add few-shot appearance learning during calibration to better match each user's phone
- [ ] Add prompts for additional poses that matter in real use: face-up, face-down, angled, partially occluded
- [ ] Decide whether calibration should adapt `iou` or `imgsz` in addition to `conf`
- [x] Log which calibration phase produced weak detections so failures are easier to debug

### Detection Quality Improvements
- [ ] Add optional image preprocessing experiments for hard cases (brightness normalization, contrast boost, resize strategy)
- [ ] Compare raw detection vs calibrated detection on the same test scenarios and document the improvement
- [ ] Add heuristics for rejecting obviously bad detections (tiny boxes, implausible aspect ratios, unstable one-frame boxes)
- [ ] Decide whether area ratio or position in frame should affect whether a detection is treated as real
- [ ] Identify the top 3 failure cases that remain after calibration and document practical mitigations

### Integration
- [x] Update `Camera` class to run calibration and apply calibrated detection parameters before live detection
- [x] Build a small test menu with the team lead so calibration and phone-detection features can be exercised quickly
- [ ] Update `Camera` class to load saved per-user calibration settings if available, fall back to defaults
- [ ] Design the full flow: first launch → calibration → save settings → live detection → re-calibrate if needed
- [ ] Decide when the app should prompt for re-calibration (manual only, or after repeated low-confidence detections)

### Training Deferred For Now
- [ ] Only revisit dataset collection and fine-tuning if calibrated detection is still unreliable on real user phones
- [ ] If that happens later, document the exact failure threshold that justifies training (for example: repeated misses after calibration across multiple orientations)

---

## Phase 5: Stretch Goals
- [ ] Try `yolo26s.pt` (small) instead of `yolo26n.pt` (nano) — is accuracy noticeably better? Is it still fast enough?
- [ ] Explore: can we detect if the user is *holding* the phone vs phone just sitting on the desk?
- [ ] Consider: should we track other distracting objects? (e.g., game controllers, food)
- [ ] Explore: can we distinguish between "checking phone briefly" vs "scrolling for minutes"?
- [ ] Revisit per-user fine-tuning later only if calibration + heuristics are not good enough

---

## Notes

### Files to Modify
- `src/vision/camera.py` — validate YOLO params, add structured output, and load saved calibration settings
- `src/vision/phone_calibration.py` — extend calibration, persistence, and detection-quality analysis
- `src/vision/test_calibration_gui.py` — keep calibration UX testable while the flow evolves
- May create a new `phone_events.py` if event logic gets complex

### Resources
- [Ultralytics YOLO Predict Docs](https://docs.ultralytics.com/modes/predict/) — conf, iou, imgsz params
- COCO class 67 = cell phone
