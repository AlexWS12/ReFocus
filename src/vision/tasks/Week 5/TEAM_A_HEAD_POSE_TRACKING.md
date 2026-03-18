# Team A - Head Pose Tracking Reliability (Week 5)

## Context
Team A's MediaPipe migration is in place. Week 5 focuses on stabilizing head-pose-based attention-state quality and making outputs easier for the Intelligence pipeline to consume.
We are not using eye-tracking as the primary signal; the core signal is head pose (yaw/pitch/roll).

## Completed in Week 4 (Carryover)
- [x] Confirmed MediaPipe dependency setup in project workflow
- [x] Replaced Haar-based path with MediaPipe-based head pose pipeline
- [x] Initialized FaceMesh/landmarker path for pose-driven attention tracking
- [x] Completed integration pass that simplified attention-state validation with the rest of vision

## Week 5 Priorities

### 1) Head-Pose State Stability
- [ ] Add temporal smoothing to attention-state transitions derived from head pose (rolling window or consecutive-frame confirmation)
- [ ] Prevent single-frame flips between ATTENTIVE and LOOKING_AWAY
- [ ] Document chosen window size and why it balances responsiveness vs stability

### 2) Structured Output Hardening
- [ ] Ensure each frame output includes consistent keys even when no face is present
- [ ] Include confidence-like score for gaze-state quality
- [ ] Add clear no-face state semantics for downstream consumers

### 3) Calibration Quality Checks
- [ ] Add calibration support for non-top camera placement (e.g., side monitor webcam, lower laptop camera)
- [ ] Add multi-screen-aware calibration by asking the user to look at all active screen corners
- [ ] Build screen boundary model from corner samples to create an allowed attention region/barrier
- [ ] Validate center/corner calibration across at least 3 lighting scenarios
- [ ] Re-run calibration after head posture changes and compare bounds drift
- [ ] Document acceptable variance for yaw/pitch/roll bounds between runs

### 4) Integration Readiness
- [ ] Verify output remains stable when phone detector overlays and guide box are active
- [ ] Confirm performance remains acceptable with attention + phone detection running together

## Deliverables
- [ ] Updated tracker logic with smoothing
- [ ] Updated calibration flow supporting off-center camera and multi-screen corner mapping
- [ ] Short test notes: false state flips before vs after smoothing
- [ ] Updated attention output schema notes for integration
