# Team A Branch Plan

## Branch Focus
Improve the iris / eye tracking pipeline so it can be integrated cleanly into the larger vision system.

## Proposed Branch Scope
- Review current camera class usage
- Define modular tracker structure
- Build or improve iris_tracker as a reusable class
- Make tracker output structured detection results
- Add attention-state logic
- Prepare for MediaPipe-based upgrade path

## Suggested Deliverables
- [ ] Confirm shared camera class interface
- [ ] Create reusable tracker class
- [ ] Make sure imports work correctly across vision files
- [ ] Return detection results as structured data
- [ ] Add basic smoothing / stability logic
- [ ] Define attention states
- [ ] Add comments and usage notes

## Proposed Output Format
Example tracker output:

    {
        "face_present": True,
        "eyes_detected": True,
        "iris_detected": True,
        "gaze_state": "center",
        "attention_confidence": 0.88,
        "state": "ATTENTIVE"
    }

## Notes
Initial prototype can use current eye detection logic, but final design should support MediaPipe Face Mesh + Iris for better stability and gaze estimation.
