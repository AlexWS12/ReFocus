# Team Lead — Architecture, Integration & Management (Jorge)

## Context
This week I'm handling project management, code reviews, and the integration layer that connects vision outputs to the rest of the app. Also responsible for codebase cleanup and making sure both teams have what they need.

Completed work this week also included the calibration animation UX, simplifying the gaze detection flow after Team A's strong MediaPipe work, building a small menu for faster feature testing with Team B, and partnering with Team B on phone calibration optimization.

---

## Management

### Code Reviews
- [x] Review Team A's MediaPipe migration PR — verify iris landmarks are correct
- [x] Review Team A's structured data output — confirm format matches agreed spec
- [x] Review Team B's calibration flow, detection heuristics, and parameter experimentation — validate their recommended values
- [ ] Review Team B's structured detection output — confirm format matches spec

### Team Support
- [x] Ensure `mediapipe` is added to `pyproject.toml` dependencies
- [ ] Answer questions from Team A on MediaPipe landmark indices
- [x] Answer questions from Team B on YOLO parameter tuning, calibration thresholds, and weak-detection filtering
- [x] Run both teams' code together and flag any integration issues early

### Planning & Communication
- [ ] Write Week 4 kickoff message in team thread — outline goals and deadlines
- [ ] Mid-week check-in — are both teams on track? Any blockers?
- [x] End-of-week review — collect findings, write Week 4 summary
- [ ] Start planning Week 5 priorities based on progress

---

## Codebase Cleanup

### Folder Reorganization
- [x] Confirm `Trackers/` folder has `__init__.py`
- [ ] Update `vision/__init__.py` — remove outdated TODOs
- [ ] Clean up any `__pycache__/` folders from old structure
- [ ] Verify all imports work after folder renames (`Trackers.iris_tracker`)

### Dependency Management
- [x] Ensure `pyproject.toml` has `mediapipe` listed
- [x] Run `uv sync` and confirm clean install
- [ ] Document any version constraints (e.g., mediapipe + Python version compatibility)

---

## Integration Layer

### Unified Vision Output
- [ ] Design a combined output format that merges Team A + Team B data:
  ```python
  {
      "timestamp": 1741500000.0,
      "attention": {
          "face_present": True,
          "gaze_state": "center",
          "attention_confidence": 0.88,
          "state": "ATTENTIVE"
      },
      "distractions": {
          "phone_detected": True,
          "phone_count": 1,
          "detections": [{"confidence": 0.87, "bbox": (x1, y1, x2, y2)}]
      }
  }
  ```
- [ ] Create `vision_pipeline.py` that orchestrates camera → tracking → detection → output
- [ ] Decide where calibration state/result lives in the pipeline so the app can reuse it across runs
- [ ] Decide how saved calibration settings and runtime detection heuristics are surfaced in the pipeline output
- [ ] Ensure the pipeline runs at acceptable FPS (target: 15+ FPS)



### Event System Design
- [ ] Design event types: `PHONE_DETECTED`, `ATTENTION_LOST`, `ATTENTION_REGAINED`, `SESSION_DISTRACTION`
- [ ] Define event payload format (timestamp, type, data)
- [ ] Decide: should events fire in real-time or batch at intervals?
- [ ] Document the event system design for both teams

---

## Hands-On Tasks

### Test Full Pipeline
- [ ] Run `camera.py` with both teams' latest code integrated
- [x] Run the new calibration flow from both `camera.py` and `test_calibration_gui.py`
- [ ] Verify saved calibration settings are reused correctly on relaunch
- [ ] Test scenario: studying normally → pick up phone → put phone down → look away → look back
- [ ] Verify that the right events/states are produced for each scenario
- [ ] Profile FPS — identify any bottlenecks

### Integration Support Completed
- [x] Improve calibration guidance animation and preview behavior so the phone-rotation prompt is easier to follow
- [x] Simplify the gaze detection path after Team A's MediaPipe work so it is easier to validate during integration
- [x] Build a small menu with Team B to make calibration and feature testing faster during development
- [x] Work with Team B on phone calibration optimization, including UX and threshold tuning

### Database Schema
- [ ] Design schema for storing study session data (attention states, distractions, timestamps)
- [ ] Prototype in `src/intelligence/database.py`
- [ ] Decide: SQLite? JSON file? What's simplest for now?

### Documentation
- [ ] Update README.md with current project state
- [ ] Document how to run the app (`uv sync` → `python main.py` or `python src/vision/camera.py`)
- [ ] Add setup instructions for new contributors

---

## Stretch Goals
- [ ] Set up basic CI — at minimum, check that imports don't break
- [ ] Create a simple config file for vision parameters (conf thresholds, FPS target, etc.)
- [ ] Prototype a minimal UI widget that shows current attention state (green = focused, red = distracted)

---

## Notes

### My Priorities This Week (in order)
1. Codebase cleanup + dependency management (unblock teams)
2. Code reviews as PRs come in
3. Integration layer design
4. Database schema prototype
5. Stretch goals if time permits

### Key Decisions to Make
- Event system architecture (Qt signals vs callbacks vs event bus)
- Database format (SQLite vs JSON)
- How calibration settings are persisted and reloaded per user
- How tightly to couple vision → UI (direct calls vs event-driven)
