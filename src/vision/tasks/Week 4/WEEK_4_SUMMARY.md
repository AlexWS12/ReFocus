# Vision Team — Week 4 Summary

## Overview
Full week sprint. Team A migrates from Haar cascades to MediaPipe (no training required). Team B focuses on improving base-model phone detection through calibration, parameter tuning, and runtime heuristics rather than custom training. Team Lead handles integration, management, and codebase cleanup.

Actual progress this week also included better calibration animation guidance, per-user few-shot phone learning, a simplified gaze-detection path built on Team A's strong work, a small test menu for faster iteration, and joint calibration optimization work between Team B and the team lead.

---

## Team A — MediaPipe Migration (Shah & Alex)
**Goal:** Replace Haar cascade eye tracker with MediaPipe Face Mesh + Iris for accurate gaze tracking.

**Key Deliverables:**
1. Rewrite `iris_tracker.py` with MediaPipe (`refine_landmarks=True` for iris)
2. Tune detection/tracking confidence parameters
3. Return structured data (gaze state, attention confidence, iris positions)
4. Define attention states: ATTENTIVE, LOOKING_AWAY, EYES_CLOSED, FACE_NOT_VISIBLE
5. Add temporal smoothing to reduce state flickering

**Important:** No model training needed — MediaPipe ships pre-trained.

---

## Team B — YOLO Optimization (Paul & Josue)
**Goal:** Build on the new calibration flow by improving detection reliability, documenting failure cases, and wiring phone detection into structured app-ready outputs without introducing manual model training yet.

**Key Deliverables:**
1. Validate and document the new calibration-derived confidence behavior alongside `iou` (0.3, 0.5, 0.7) and `imgsz` (320, 640, 1280)
2. Document detection limits (distance, angle, lighting, similar objects)
3. Return structured detection data (phone_detected, confidence, bbox, area_ratio)
4. Implement detection events (PHONE_APPEARED, PHONE_GONE) with cooldown
5. Persist and reuse per-user calibration settings, and add practical heuristics to reduce weak detections

**Week 4 progress highlights:**
1. Improved phone-calibration guidance with animated rotation previews and clearer prompts
2. Added few-shot appearance learning so calibration better matches each user's phone across multiple views
3. Worked with the lead on calibration optimization and faster test loops through a small menu

---

## Team Lead — Integration & Management (Jorge)
**Goal:** Keep teams unblocked, clean up codebase, build the integration layer.

**Key Deliverables:**
1. Code reviews for both teams' PRs
2. Codebase cleanup (folder structure, `__init__.py` files, dependencies)
3. Design unified vision output format (attention + distraction data)
4. Prototype vision → app event system
5. Database schema for study session data
6. Mid-week and end-of-week check-ins

**Week 4 progress highlights:**
1. Improved the calibration animation/preview flow so the phone rotation steps are easier to follow
2. Simplified the gaze detection path on top of Team A's strong MediaPipe implementation
3. Built a small menu with Team B to test calibration and related features more quickly
4. Partnered with Team B on phone calibration optimization and validation

---

## Week 4 Priorities (ranked)
1. **Team A:** Get MediaPipe running and returning iris landmarks
2. **Team B:** Validate the new calibration flow and document optimal YOLO parameters
3. **Lead:** Codebase cleanup and dependency management
4. **Team A:** Structured attention data output
5. **Team B:** Structured detection data output and saved calibration settings
6. **Lead:** Integration layer connecting calibration + vision to app
7. **All:** Event system design for vision → UI communication
