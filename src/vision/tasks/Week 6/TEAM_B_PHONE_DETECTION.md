# Team B - Calibration and Detection Integration Cleanup (Week 6)

## Context
Phone calibration and few-shot validation are in place. Week 6 shifts toward integration cleanliness: calibration should stay isolated to calibration flows, runtime camera should stay lightweight, and detection behavior should be robust enough for the main app to consume without hidden side effects.

## Completed in Week 5 (Carryover)
- [x] Interactive calibration flow with guide box + rotation phases is in place
- [x] Few-shot bundle persistence is wired into runtime camera behavior
- [x] Camera no longer auto-runs calibration on direct startup
- [x] Menu flow isolates launch-camera from calibration actions

## Week 6 Priorities

### 1) Runtime/Calibration Separation
- [x] Ensure calibration is launched only from menu/calibration helpers, not camera startup
- [x] Keep heavy calibration imports lazy so non-calibration paths stay lightweight
- [ ] Re-check that detector calibration helpers are not leaking calibration-specific state into runtime camera flow

### 2) Detection Robustness
- [ ] Add integration notes for how permissive few-shot thresholds should be in noisy environments
- [ ] Review fallback-detection behavior for cases where appearance matching briefly drops good detections
- [ ] Confirm detection remains understandable when calibration bundle is missing or partially invalid

### 3) Cross-Team Handoff Readiness
- [x] Keep vision responsible only for capture/detection/calibration helpers
- [x] Avoid DB/bootstrap logic inside vision runtime code
- [ ] Document any runtime assumptions the UI/intelligence teams must satisfy (camera availability, calibration files, dependencies)

## Deliverables
- [x] Cleaner camera/calibration separation
- [x] Lightweight import flow for runtime helper modules
- [ ] Brief handoff note covering calibration/runtime expectations


## Notes from tuesday 31 meeting
- create a set that has disctractions in camera.py where distractions (look away, phone, left desk) can be unabled by the user and therefore not read by camera.py during a study session
- correct the detection, the session starts when the button is clicked but there is a delay where the screen freezes, the detection also starts when the button is clicked, it shouldn't (add a delay)
- 