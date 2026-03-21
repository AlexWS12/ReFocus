# Vision Module

Real-time phone detection and head-pose attention tracking for StudyWidget.
Runs as a background loop feeding distraction events into `SessionManager`.

---

## Folder Structure

```
src/vision/
├── camera.py                   # Main detection loop — YOLO + DINO + attention tracker, distraction logging
├── menu.py                     # CLI startup menu: launch camera, phone calibration, gaze calibration
├── detectors/
│   ├── dino_detector.py            # Grounding DINO zero-shot phone detector (lazy-loads HuggingFace weights)
│   ├── dino_calibration_widget.py  # PySide6 UI for the DINOv2 phone calibration flow
│   └── phone_calibration.py        # Interactive per-user phone calibration (guide box + rotation phases + few-shot learning)
├── tests/
│   ├── conftest.py                 # Shared pytest fixtures for mock camera + SessionManager wiring
│   ├── test_camera_distractions.py # Pytest integration tests for phone/look-away/left-desk logging
│   ├── test_calibration_gui.py     # Interactive calibration GUI test (marked skipped in pytest)
│   └── __init__.py
├── phone_few_shot_bundle.npz   # Persisted calibration output: appearance signatures + tuned thresholds
├── Trackers/
│   ├── attention_tracker.py    # MediaPipe head-pose tracker; outputs attention state (ATTENTIVE / AWAY)
│   ├── gaze_calibration.py     # Corner-based gaze calibration — records yaw/pitch bounds per user
│   ├── gaze_center_calibration.json  # Persisted calibration profile (gitignored — generated at runtime)
│   └── face_landmarker.task    # MediaPipe model bundle for face landmark detection
├── assets/
│   └── animations/             # UI animation assets for calibration guidance
└── tasks/                      # Sprint planning and weekly summary docs
    ├── Week 3/
    ├── Week 4/
    └── Week 5/
```

---

## Key Files

### `camera.py`
Central detection loop. On every frame:
1. **YOLO** (every Nth frame, frame-skipped for speed) detects cell phones via `classes=[67]`.
2. **Grounding DINO** runs supplementally every 5 frames or immediately when YOLO finds nothing — catches misses at a slightly lower confidence threshold.
3. Candidates are deduplicated via IoU, spatially filtered (guide-box gate when uncalibrated), and appearance-filtered (cosine similarity against few-shot exemplars when calibrated).
4. The winning detection is annotated and passed to **distraction tracking**.
5. **`gazeTracker`** overlays head-pose state (ATTENTIVE / AWAY) on the frame.
6. **`_update_distraction_tracking`** calls `session_manager.log_distraction()` when events resolve.

Accepts an optional `session_manager` argument:
```python
from camera import Camera
cam = Camera(session_manager=my_session_manager)
```

### `menu.py`
CLI entry point for the vision subsystem. Options:
- Launch camera loop
- Run phone calibration
- Run gaze center calibration

### `phone_calibration.py`
Multi-phase interactive calibration:
1. **Static phase** — user holds phone still inside guide box; YOLO detections are collected.
2. **Rotation phase** — user rotates phone through several orientations; appearance descriptors are sampled.
3. **Validation** — user accepts or retries the captured set.

Output is saved to `phone_few_shot_bundle.npz` and loaded automatically by `Camera` on next startup.

### `dino_detector.py`
Wraps `IDEA-Research/grounding-dino-tiny` from HuggingFace. Weights are downloaded on first use and cached. When the package is unavailable the detector silently returns no boxes, so the rest of the pipeline is unaffected.

Typical latency: ~80–200 ms on GPU, ~300–800 ms on CPU.

### `Trackers/attention_tracker.py`
MediaPipe Face Landmarker–based head-pose tracker. Runs at a capped rate (~5 Hz) to avoid overloading the frame loop. Reports:
- `face_facing_screen` — bool
- `attention_state` — `"attentive"` | `"away"` | `"no_face"`
- `yaw_deg`, `pitch_deg`, `roll_deg` — corrected head-pose angles

### `Trackers/gaze_calibration.py`
Corner-based gaze calibration. Asks the user to look at each screen corner, recording the resulting head-pose bounds. This lets the attention tracker handle off-center camera placement and multi-monitor setups correctly.

---

## Distraction Logging

`Camera._update_distraction_tracking()` bridges vision into `SessionManager`:

- **Phone distraction** — opens when a phone is first accepted; stays open during a 5-second cooldown so brief flickers don't split one event into many; logs via `log_distraction(PHONE_DISTRACTION, duration)` when the cooldown expires.
- **Look-away distraction** — same cooldown logic using head-pose `face_facing_screen`.
- **Priority suppression** — phone takes priority only while events overlap in the same frame; phone cooldown does not suppress non-phone tracking.
- **Flush on exit** — `Camera.release()` calls `_flush_open_distractions()` so any event still open when the camera closes is logged using `last_seen` as the end time (not the shutdown timestamp).

---

## Running

```bash
# From src/vision/
python menu.py

# Or directly:
python camera.py   # runs calibration then opens the detection window
```

Press `q` in the OpenCV window to quit.

---

## Test Isolation (Vision + Intelligence)

The test setup now isolates test code from functional runtime code while preserving vision ↔ intelligence integration:

- **Pytest-based test suite** — configured in `pyproject.toml` with test paths:
    - `src/vision/tests`
    - `src/intelligence/tests`
- **Shared fixtures in `conftest.py`** create mock camera state and test-specific SessionManager instances.
- **File-based test DBs** are used intentionally and cleaned up after each test run.
- **Interactive GUI calibration test** is intentionally skipped in automated pytest runs.
- **Direct-run support retained** for debugging (`python .../test_*.py`) with runtime import fallback comments in test files.

### Test Commands

```bash
# Run all tests from project root
python -m pytest -q

# Run only vision tests
python -m pytest src/vision/tests -v

# Run only intelligence tests
python -m pytest src/intelligence/tests -v
```

---

## Sprint History

| Week | Focus | Key Outcomes |
|------|-------|-------------|
| 3 | Foundation | YOLO phone detection + Haar-cascade eye tracking merged into unified `camera.py` |
| 4 | Migration & Calibration | MediaPipe head-pose replaces Haar; interactive phone calibration with few-shot appearance learning shipped |
| 5 | Correctness Sprint | Grounding DINO added as fallback detector; ByteTrack added for frame-to-frame continuity; distraction event logging with cooldown + priority wired into `SessionManager`; corner-based gaze calibration scoped for off-center cameras and multi-screen setups |

Full sprint notes are in `tasks/Week X/WEEK_X_SUMMARY.md`.
