# Hand Mouse Controller

> Natural hand-gesture driven control for mouse, media, volume and real‑time speech dictation. Built with Computer Vision (MediaPipe + OpenCV), a modern CustomTkinter GUI and system integration libraries. Designed as a portfolio / research style project showcasing practical multimodal interaction.

<p align="center">
    <img src="icon_preview.png" alt="HandMouse Icon" width="120" />
    <br>
    <em>Control your PC with intuitive, ergonomic hand & finger gestures.</em>
</p>

## Table of Contents
1. Overview
2. Core Features
3. Gesture Reference
4. Architecture & Modules
5. Technology Stack
6. Installation (Dev) & Requirements
7. Quick Start
8. Configuration & Settings
9. Building a Standalone EXE
10. Performance & Design Decisions
11. Troubleshooting
12. Roadmap / Future Ideas
13. Contributing Guidelines
14. License

## 1. Overview
Hand Mouse Controller turns any standard webcam into an interaction layer: your right hand becomes a precision mouse and your left hand controls system volume & media playback—plus continuous speech recognition for dictation. It aims to demonstrate:
- Practical CV integration (MediaPipe Hands) with responsive UI.
- Human‑centered gesture set balancing discoverability, ergonomics and minimal false positives.
- Clean modular Python architecture for extensibility (add more gestures or subsystems easily).
- Portfolio presentation: clear documentation, reproducible build, production style config management.

## 2. Core Features
### Right Hand – Mouse
- Palm tracking → pointer movement (adaptive smoothing).
- Pinch variations → left / right / double click.
- Scroll mode (index finger) with stabilized vertical mapping.
- Drag‑and‑drop via sustained left pinch.
- Mouse pause (fist) without shutting camera.

### Left Hand – Audio & Media
- Enable/disable subsystem with a fist gesture.
- Continuous volume ramp up/down via directional movement in volume mode.
- Mute toggle (three finger pinch).
- Media play/pause (two finger pinch).

### Global & System
- Global pause (both index fingertips touching) freezes all actions safely.
- Overlay HUD: live FPS, hand presence, gesture name, speech status.
- Persistent settings saved to JSON (AppData when frozen as EXE) + runtime reload.

### Speech Dictation
- Continuous microphone listening (configurable language: Turkish / English).
- Fast text injection via clipboard + simulated paste for minimal latency.
- Optional auto‑enter mode after phrase completion.

### GUI
- CustomTkinter responsive panel (camera view + control tabs).
- Scrollable settings with fixed save button.
- Dedicated help modal describing gestures (recruiter friendly showcase).

## 3. Gesture Reference
| Domain | Gesture | Fingers / Shape | Action |
|--------|---------|-----------------|--------|
| Mouse | Open Palm | Relaxed | Move pointer |
| Mouse | Thumb + Index Pinch | 2 fingers | Left click / drag while held |
| Mouse | Thumb + Middle Pinch | 2 fingers | Right click |
| Mouse | Thumb + Index + Middle Pinch | 3 fingers | Double click (one-shot) |
| Mouse | Index Extended (scroll mode) | 1 finger | Vertical scroll mapping |
| Mouse | Fist | Closed hand | Toggle mouse pause |
| Global | Both Index Together | 2 hands | Global pause / resume |
| Audio | Left Fist | Closed hand | Enable / disable audio gestures |
| Audio | Two Finger Pinch (Left) | Thumb + Index | Media play/pause |
| Audio | Three Finger Pinch (Left) | Thumb + Index + Middle | Mute toggle |
| Audio | Volume Mode | Index + Middle up | Enter volume adjust mode |
| Audio | Volume Up | Upward movement | Ramp increase |
| Audio | Volume Down | Downward movement | Ramp decrease |
| Speech | (Automatic) | — | Continuous dictation if enabled |

Design: High specificity gestures (three finger pinch) override less specific states to reduce collision. All toggles are single‑action, repeat protected via internal flags.

## 4. Architecture & Modules
```
src/
├── config.py            # Central configuration + startup loader
├── config_manager.py    # Persistence (JSON path selection normal vs EXE)
├── gui_app.py           # CustomTkinter application (main GUI class)
├── hand_detector.py     # MediaPipe hand landmark acquisition
├── gesture_recognizer.py# Gesture logic & state machines
├── mouse_controller.py  # Coordinate mapping + click / scroll abstraction
├── volume_controller.py # System audio & media control (pycaw, Win32)
├── speech_to_text.py    # SpeechRecognition wrapper + fast paste
├── overlay_display.py   # Lightweight HUD overlay
└── __init__.py
```
Separation encourages testability and future augmentation (e.g., add head pose, multi‑hand cooperative gestures, or plugin style input sources).

## 5. Technology Stack
- Python 3.10
- MediaPipe & OpenCV – real‑time landmark detection + frame processing.
- PyAutoGUI + Win32 APIs – robust pointer & window interaction.
- Pycaw / COM – volume & media control abstraction.
- SpeechRecognition + PyAudio – microphone streaming + Google speech engine.
- CustomTkinter – modern themed GUI components.
- Clipboard + paste injection – low latency text commit strategy.

## 6. Installation (Development)
Prerequisites: Python 3.10 (Windows target), a webcam, functioning microphone.
```bash
git clone https://github.com/<your-account>/HandMouse.git
cd HandMouse
python -m venv .venv
".venv\Scripts\activate"
pip install -r requirements.txt
```

If PyAudio fails on Windows, install wheel:
```bash
pip install pipwin
pipwin install pyaudio
```

## 7. Quick Start
Run GUI (recommended):
```bash
python gui_main.py
```
Run console variant (minimal overlay, primarily for debugging):
```bash
python main.py
```

Save settings → close application → reopen to apply (EXE mode requires full restart to reload JSON at import time).

## 8. Configuration & Settings
Runtime configuration lives in `settings.json` (auto‑created). For source control hygiene, prefer tracking an example:
```jsonc
// settings.example.json
{
    "CAMERA_INDEX": 0,
    "CAMERA_FPS": 60,
    "CAMERA_CROP_LEFT": 0.10,
    "CAMERA_CROP_RIGHT": 0.10,
    "CAMERA_CROP_TOP": 0.10,
    "CAMERA_CROP_BOTTOM": 0.10,
    "MAX_HANDS": 2,
    "MOUSE_SPEED": 3.0,
    "EMA_MIN": 0.02,
    "EMA_MAX": 0.60,
    "EMA_FUNCTION": "sigmoid",
    "SHOW_FPS": true,
    "SHOW_LANDMARKS": true,
    "SHOW_GESTURE_TEXT": true,
    "FLIP_CAMERA": true,
    "VOLUME_STEP": 4,
    "SPEECH_LANGUAGE": "tr-TR",
    "SPEECH_MICROPHONE_INDEX": null
}
```
On module import, `config.py` loads current JSON into the `Config` class enabling hot reload via `importlib.reload` on full restart.

## 9. Building a Standalone EXE
Generates a portable binary (no Python required on target machine):
```bash
py -3.10 build_exe.py
```
Output: `dist/HandMouse.exe`.
The build script bundles required libraries (MediaPipe, OpenCV, CustomTkinter etc.) and writes settings to `%APPDATA%/HandMouse/settings.json` in frozen mode.

## 10. Performance & Design Decisions
- Buffer size reduction (`CAP_PROP_BUFFERSIZE=1`) to minimize camera latency.
- EMA smoothing bounds (min/max + function selection) exposed for experimentation.
- Clipboard paste vs. keyboard simulation for speech results → significantly faster insertion & reduced key event overhead.
- Gesture evaluation order: specific → general, lowering accidental triggers.
- Overlay decoupled from main loop for UI clarity without heavy rendering cost.

## 11. Troubleshooting
| Issue | Cause | Resolution |
|-------|-------|-----------|
| Camera not opening | In‑use or wrong index | Adjust CAMERA_INDEX in settings.json |
| High latency pointer | FPS too low / crop too tight | Increase FPS / adjust crop margins |
| Speech not detected | Microphone permission / PyAudio | Reinstall PyAudio, test mic in OS settings |
| EXE settings ignore change | No restart after save | Close & reopen EXE (reload occurs at import) |
| Volume gestures flaky | Lighting / landmark loss | Improve lighting, reduce hand distance |

## 12. Roadmap / Future Ideas
- Multi‑platform support (Linux / macOS abstraction layers).
- Adaptive gesture learning (personal calibration phase).
- Head pose or gaze assisted pointer acceleration.
- Advanced dictation: punctuation inference & language auto‑switch.
- Plugin architecture for third‑party gesture packs.
- Unit tests + CI for core recognition logic.

## 13. Contributing
While primarily a portfolio project, constructive improvements are welcome:
1. Fork & create feature branch.
2. Keep changes modular (one concern per PR).
3. Add/update documentation if behavior changes.
4. Avoid committing personal `settings.json`.

## 14. License
License to be determined (TBD). For evaluation / personal use. If you intend broader distribution, please open an issue to clarify licensing terms.

---
### Why This Project Matters (Recruiter / Reviewer Note)
This codebase reflects: clean modular design, thoughtful UX for non‑traditional input, performance awareness (latency, smoothing), and pragmatic engineering (restart reload model, robust build pipeline). It balances experimentation with maintainability—showing ability to integrate CV, GUI, system APIs and speech in a cohesive product.

Feel free to reach out with questions or suggestions.

---
<p align="center">Built with curiosity and a focus on human interaction ✨</p>
