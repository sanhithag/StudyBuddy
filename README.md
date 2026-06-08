# StudyBuddy AI

A desktop study companion that uses your webcam to monitor focus, detect drowsiness, and help you build better study habits — all running locally on your machine.

---

## Features

**Real-time biometric monitoring**
- Face presence detection — alerts you if you step away
- Drowsiness detection using Eye Aspect Ratio (EAR)
- Distraction detection via head pose estimation (yaw/pitch)
- Fatigue detection based on blink rate and focus transitions
- Posture detection using ear-to-shoulder alignment

**Three study modes**
- **Deep Work** — no timer, no interruptions; you decide when to stop
- **Smart Session** — AI monitors your focus and suggests breaks when your biometrics indicate fatigue
- **Custom** — you set your own study and break durations

**Adaptive session planning**
After each session, the engine adjusts your next study/break split based on your focus score — shorter blocks if you're struggling, longer ones if you're in flow.

**Statistics dashboard**
- Session history table
- Focus score averages, total hours, active days per week
- Streak tracking (current and best)
- Personalised coaching insight based on your averages

**Account system**
- Registration with security question for password recovery
- Persistent login via secure session token
- Profile with avatar colour picker and daily study goal
- Password change and account deletion

---

## Requirements

- Python 3.10+
- Webcam

Install dependencies:

```bash
pip install PyQt6 opencv-python mediapipe scipy bcrypt
```

---

## Setup & Running

```bash
# Clone or download the project
cd "studysense ai"

# Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install PyQt6 opencv-python mediapipe scipy bcrypt

# Run
python main.py
```

On first launch, StudyBuddy will automatically download two MediaPipe model files (~10 MB total) into an `assets/` folder. This only happens once.

---

## Project Structure

```
studysense ai/
│
├── main.py            # Entry point; owns the QStackedWidget router and all page wiring
├── pages.py           # All UI pages (Login, Workspace, Stats, Profile, Settings, …)
├── biometric.py       # Webcam analysis engine (drowsiness, distraction, fatigue, posture)
├── camera_thread.py   # Dedicated QThread for camera capture and frame processing
├── storage.py         # SQLite persistence layer (auth, sessions, analytics, tokens)
├── theme.py           # Colour palette and global QSS stylesheet
├── widgets.py         # Reusable widgets (StatCard, AvatarCircle, MessageBanner, …)
│
├── assets/            # Auto-downloaded MediaPipe model files (created on first run)
│   ├── face_landmarker.task
│   └── pose_landmarker.task
│
└── data/              # SQLite database and session token (created on first run)
    ├── StudyBuddy.db
    └── session.json
```

---

## How It Works

1. **Login / Register** — accounts are stored in a local SQLite database. Passwords are hashed with bcrypt. Login state is persisted via a random token stored in `data/session.json` (token is validated against the database on startup).

2. **Session Select** — choose Deep Work, Smart Session, or Custom. The camera begins warming up in a background thread while you choose.

3. **Workspace** — the camera feed is processed at ~30 fps on a dedicated thread. The biometric engine runs MediaPipe face and pose landmark detection on each frame and emits a status (`Focused`, `WARNING: DROWSY`, `NOT FOCUSED`, `FATIGUED`, `POOR POSTURE`, `FACE NOT FOUND`). A HUD overlay is drawn directly onto the video frame showing live metrics (EAR, yaw, pitch, blink rate).

4. **Break suggestions** — in Smart/Custom modes, a break dialog is shown once per session when enough focus-to-unfocused transitions accumulate within a rolling window, or at 55% of session time as a backstop.

5. **Session end** — focus score and session metadata are saved to the database. The adaptive planner adjusts the next session's study/break split based on your score.

---

## Biometric Thresholds

These are tunable constants at the top of `biometric.py`:

| Constant | Default | Meaning |
|---|---|---|
| `EAR_CLOSED_THRESH` | 0.20 | Eye aspect ratio below this = eye closed |
| `DROWSY_FRAMES` | 20 | Consecutive closed frames before drowsy alert (~0.7 s) |
| `GAZE_YAW_THRESH` | 35° | Head turn angle before distraction alert |
| `GAZE_PITCH_THRESH` | 30° | Head tilt angle before distraction alert |
| `DISTRACT_FRAMES` | 90 | Frames looking away before NOT FOCUSED (~3 s) |
| `HIGH_BLINK_RATE` | 25 /min | Blinks per minute above this = eye fatigue |
| `FATIGUE_TRANSITIONS` | 3 | Focus→unfocused transitions in 15 min = FATIGUED |
| `SLOUCH_RATIO_THRESH` | 0.12 | Ear-to-shoulder ratio below this = poor posture |
| `POSTURE_FRAMES` | 90 | Frames slouching before POOR POSTURE alert |

---

## Database Schema

```
users               — username, bcrypt password hash, profile fields
sessions            — per-session focus scores and durations
security_questions  — bcrypt-hashed answers for password recovery
session_tokens      — random opaque login tokens (expire after 30 days)
study_analytics     — streak counters and last-study date
```

---

## Troubleshooting

**Camera doesn't start**
Make sure no other application is using the webcam. On Windows, CAP_DSHOW is used automatically; on macOS/Linux the default backend is used.

**Models fail to download**
Check your internet connection. You can also manually download the files and place them in the `assets/` folder:
- `face_landmarker.task` — https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
- `pose_landmarker.task` — https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task

**`sqlite3.IntegrityError: NOT NULL constraint failed: users.salt`**
You have a database from before the bcrypt migration. Replace `storage.py` with the latest version — it will automatically migrate your existing database on next launch, preserving all your data.

**Gaze detection feels off**
Once a session is active, a **⊕ Calibrate Gaze** button appears below the camera feed. Click it to set your current head position as the neutral reference point — useful if you've shifted in your seat or distraction alerts are firing when they shouldn't be. A "✓ Calibrated" confirmation appears briefly then fades. The button is hidden while on a break or between sessions.