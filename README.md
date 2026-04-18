# Study Tracker Partner - Team Structure
<img width="6912" height="3456" alt="image" src="https://github.com/user-attachments/assets/4d01d969-0f6a-48a1-af36-eba1ceb10a8a" />

## How We Collaborate

- **Groups & Ownership**
  - **VISION**: Webcam, face/phone detection, screen monitoring (no UI, no DB).
  - **INTELLIGENCE**: Data, database, statistics, insights (no camera, no Qt UI).
  - **EXPERIENCE**: Desktop UI, pet companion, gamification (no OpenCV/YOLO, no raw DB).
- **Shared Contracts**
  - Common **events and data models** live in `src/core/` so groups share types without importing each other’s internals.
  - Changes to `core/` are proposed and agreed across groups (short issues/Discord messages).
- **Integration**
  - Only the **app layer** (e.g. `main.py` or `src/app/`) knows about all three groups.
  - VISION emits events → EXPERIENCE updates UI/pet → INTELLIGENCE stores & analyzes sessions → EXPERIENCE shows stats and insights.
- **Ways of Working**
  - Group-level standups; async updates via **Discord**; tasks tracked in **Trello**; code review via **GitHub PRs**.
  - Everyone can jump in as **Debugger** and **Researcher** across groups when needed.

## Codebase Structure (High-Level)

```text
src/
  core/           # Shared events, models, optional interfaces (no UI, CV, or DB logic)
  vision/         # VISION-only: capture, detection, screen monitor, event emitter facade
  intelligence/   # INTELLIGENCE-only: DB schema, queries, stats, insights facade
  experience/     # EXPERIENCE-only: PySide6 UI (windows, tabs, widgets, styles)
  app/ (optional) # Wiring/bootstrap: creates services, connects signals, starts UI
```

- **Rule:** `vision/`, `intelligence/`, and `experience/` never import each other directly; they depend only on `core/` and are wired together in the app layer.

## Project Overview

- **Goal:** Desktop study companion that tracks focus via webcam, detects distractions, and rewards focused time with points, levels, achievements, and an animated pet.
- **Flow:** VISION detects focus/distractions → EXPERIENCE reacts in real time → session stored and analyzed by INTELLIGENCE → EXPERIENCE surfaces stats and insights in the UI.
