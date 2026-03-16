# Team Lead - Week 5 Integration and Quality Gate

## Context
Week 5 focus is quality assurance across the full attention + phone pipeline, with emphasis on phone-label correctness in real-world conditions.

## Completed in Week 4 (Carryover)
- [x] Reviewed Team B calibration flow, heuristics, and parameter experiments
- [x] Supported Team B on threshold tuning and weak-detection filtering
- [x] Ran both teams' code together and surfaced early integration issues
- [x] Ensured MediaPipe dependency inclusion in project dependencies
- [x] Ran calibration flow from camera path and test GUI path
- [x] Improved calibration guidance animation and preview behavior
- [x] Simplified gaze-detection validation path after Team A migration
- [x] Built menu flow for faster calibration and feature testing
- [x] Partnered with Team B on phone-calibration optimization (UX + thresholds)

## Management Priorities
- [ ] Confirm Team B's labeling validation protocol is executed and documented
- [ ] Ensure Team A and Team B smoothing choices do not conflict in responsiveness
- [ ] Review threshold defaults before merge (confidence, overlap, few-shot, temporal)

## Integration Tasks

### 1) Unified Detection Contract
- [ ] Define final accepted-phone criteria in one place:
  - in guide region by overlap ratio
  - passes few-shot similarity
  - passes temporal consistency window
- [ ] Require reason-coded rejection path for debugging

### 2) Observability
- [ ] Add lightweight runtime telemetry counters:
  - total phone candidates
  - accepted detections
  - rejected by overlap
  - rejected by few-shot
  - rejected by temporal gate
- [ ] Surface counters in logs or debug panel for quick diagnosis

### 3) Performance and UX Balance
- [ ] Verify gates do not reduce FPS below target
- [ ] Confirm user-facing prompts remain clear when detection is rejected
- [ ] Keep guide-box messaging actionable (not generic failures)

### 4) Release Readiness Criteria
- [ ] Precision target agreed and met on validation set
- [ ] False positives in empty-box scenario below agreed threshold
- [ ] No severe flicker in phone present/gone events
- [ ] Calibration overwrite behavior verified across repeated runs

## Deliverables
- [ ] Integration checklist signed off
- [ ] Short release note summarizing reliability gains and remaining risks
