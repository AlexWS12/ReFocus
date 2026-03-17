# Team A - Gaze Tracking Reliability (Week 5)

## Context
Team A's MediaPipe migration is in place. Week 5 focuses on stabilizing attention-state quality and making outputs easier for the Intelligence pipeline to consume.

## Completed in Week 4 (Carryover)
- [x] Confirmed MediaPipe dependency setup in project workflow
- [x] Replaced Haar-based eye tracking path with MediaPipe-based approach
- [x] Initialized FaceMesh/landmarker path for iris-aware tracking flow
- [x] Completed integration pass that simplified gaze-detection validation with the rest of vision

## Week 5 Priorities

### 1) Gaze-State Stability
- [ ] Add temporal smoothing to gaze-state transitions (rolling window or consecutive-frame confirmation)
- [ ] Prevent single-frame flips between ATTENTIVE and LOOKING_AWAY
- [ ] Document chosen window size and why it balances responsiveness vs stability

### 2) Structured Output Hardening
- [ ] Ensure each frame output includes consistent keys even when no face is present
- [ ] Include confidence-like score for gaze-state quality
- [ ] Add clear no-face state semantics for downstream consumers

### 3) Calibration Quality Checks
- [ ] Validate center/corner gaze calibration across at least 3 lighting scenarios
- [ ] Re-run calibration after head posture changes and compare bounds drift
- [ ] Document acceptable variance for yaw/pitch/roll bounds between runs

### 4) Integration Readiness
- [ ] Verify output remains stable when phone detector overlays and guide box are active
- [ ] Confirm performance remains acceptable with attention + phone detection running together

## Deliverables
- [ ] Updated tracker logic with smoothing
- [ ] Short test notes: false state flips before vs after smoothing
- [ ] Updated attention output schema notes for integration
