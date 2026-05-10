# StudyBuddy AI

A Pomodoro focus tracker with real-time facial biometric analysis.  
Detects drowsiness and distraction via webcam, adapts your study/break
blocks based on focus history, and persists everything to a local SQLite DB.

---

## File structure

```
StudyBuddy/
├── main.py            ← Entry point — wires all pages together
├── pages.py           ← All PyQt6 page classes (Login, Register, …)
├── widgets.py         ← Reusable UI components (StatCard, AvatarCircle, …)
├── theme.py           ← Colour palette + global QSS stylesheet
├── biometric.py       ← OpenCV + MediaPipe engine (no UI imports)
├── camera_thread.py   ← QThread that feeds frames to the engine
├── storage.py         ← All SQLite calls (auth, profile, sessions)
├── requirements.txt
├── assets/            ← face_landmarker.task downloaded here on first run
└── data/
    └── StudyBuddy.db  ← Created automatically on first run
```

---

## Setup

```bash
# 1. Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

On first launch the MediaPipe face-landmarker model (~29 MB) is
downloaded automatically to `assets/face_landmarker.task`.

---

## Features

| Feature | Detail |
|---|---|
| **Secure auth** | Passwords hashed with SHA-256 + random salt |
| **Register** | Username, full name, email, security question |
| **Forgot password** | Security-question-based self-service reset |
| **Profile page** | Edit name, email, daily goal, avatar colour |
| **Change password** | Requires current password verification |
| **Focus tracking** | EAR-based drowsiness + iris-tracking distraction |
| **Adaptive Pomodoro** | Study/break durations auto-adjust to focus score |
| **Stats page** | Per-session history table + AI coach tip |
| **Settings** | Update security question, wipe history, delete account |

---

## Architecture notes

- **`storage.py`** has zero UI imports — it can be tested or replaced independently.
- **`biometric.py`** has zero UI or DB imports — pure computer-vision logic.
- **`camera_thread.py`** is the only place threading happens; it emits `frame_ready` signals.
- **`pages.py`** builds all QWidget pages; they communicate only via signals.
- **`main.py`** is the router: it listens to signals and swaps pages in the QStackedWidget.
