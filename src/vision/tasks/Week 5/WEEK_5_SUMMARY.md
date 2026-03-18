# Week 5 Summary - Detection Correctness Sprint

## Objective
Improve phone labeling correctness beyond box-only gating by combining spatial, appearance, and temporal validation.

## Completed in Week 4 (Carryover)
- [x] Interactive phone calibration flow shipped (guide box + rotation phases)
- [x] Calibration validation UX shipped (accept/retry/cancel)
- [x] Rotation guidance improvements shipped (animation + clearer prompts)
- [x] Few-shot appearance learning introduced in calibration flow
- [x] Team test menu flow added for quicker validation loops
- [x] Gaze-tracking integration path simplified for cross-team testing

## Key Technical Direction
- Spatial gate: overlap ratio with guide box (not center-only)
- Appearance gate: persisted few-shot similarity
- Temporal gate: N-of-M frame consistency
- Sanity gate: geometric plausibility checks
- Evaluation: precision/recall + rejection-reason analytics

## Team Focus
- Team A: gaze-state smoothing and calibration consistency
- Team B: phone-label correctness implementation + metrics
- Team Lead: integration contract, telemetry, release gating

## Team Lead Implementation Update (Completed)
- Researched practical methods to improve phone-recognition correctness and selected YOLO + Grounding DINO hybrid detection.
- Enabled ByteTrack on the YOLO path using `self.model.track(..., tracker="bytetrack.yaml", persist=True, verbose=False)` to maintain Kalman-filtered track continuity between frames.
- Extracted per-detection track IDs from `box.id` and extended detection candidates to include track identity: `(x1, y1, x2, y2, conf, source, track_id)`.
- Kept DINO candidates trackless (`track_id=None`) since ByteTrack applies only to YOLO outputs.
- Added track-aware appearance gating: when current detection matches last confirmed track, lowered similarity threshold by `0.05` (with a floor at `0.30`) to reduce dropouts during rotation/occlusion.
- Added `_active_track_id` lifecycle update each frame, resetting to `None` when no phone is accepted.
- Updated annotation format to include tracking context (example: `PHONE(YOLO #3) 87%  sim:0.71`).

## Exit Criteria
- False positives reduced in guide-box scenarios
- Minimal detection flicker
- Thresholds documented and reproducible
- Runtime behavior understandable through reason-coded rejects
