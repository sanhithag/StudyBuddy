"""
biometric.py — StudyBuddy AI
Full detection pipeline:
  1. Face presence
  2. Drowsiness  (EAR + frame buffer)
  3. Distraction (head-pose yaw/pitch via solvePnP, frame buffer)
  4. Fatigue     (high blink frequency + AIE transition counter)
  5. Posture      (ear-shoulder ratio via MediaPipe Pose)

Priority order (checked top-to-bottom, first match wins):
  FACE NOT FOUND → DROWSY → NOT FOCUSED → FATIGUED → POOR POSTURE → Focused
"""

import math
import time
import threading
import urllib.request
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from scipy.spatial import distance as dist

from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python import BaseOptions

# ──────────────────────────────────────────────────────────────────────────────
# Model assets
# ──────────────────────────────────────────────────────────────────────────────

_ASSET_DIR = Path(__file__).parent / "assets"

FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
FACE_MODEL_PATH = _ASSET_DIR / "face_landmarker.task"

POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
POSE_MODEL_PATH = _ASSET_DIR / "pose_landmarker.task"


def ensure_models(progress_cb=None) -> None:
    _ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for url, path in [(FACE_MODEL_URL, FACE_MODEL_PATH),
                      (POSE_MODEL_URL, POSE_MODEL_PATH)]:
        if path.exists():
            continue

        def _hook(b, bs, tot, p=path):
            if progress_cb and tot > 0:
                progress_cb(p.name, min(100, int(b * bs * 100 / tot)))

        urllib.request.urlretrieve(url, path, _hook)


# ──────────────────────────────────────────────────────────────────────────────
# Tunable thresholds
# ──────────────────────────────────────────────────────────────────────────────

EAR_CLOSED_THRESH   = 0.20   # EAR below this → eye closed
DROWSY_FRAMES       = 20     # consecutive closed frames → drowsy (~0.7 s)

GAZE_YAW_THRESH   = 35.0     # Allows more side-to-side movement
GAZE_PITCH_THRESH = 30.0     # Allows more up/down movement
DISTRACT_FRAMES   = 90       # ~3 seconds of looking away

BLINK_WINDOW_SECS   = 60     # rolling window for blink rate
HIGH_BLINK_RATE     = 25     # blinks/min above this → eye fatigue

SLOUCH_RATIO_THRESH = 0.12   # ear-above-shoulder ratio below this → slouch
POSTURE_FRAMES       = 90     # frames of bad posture before alert

FATIGUE_TRANSITIONS   = 3    # focus→distracted transitions in 15m window
FATIGUE_WINDOW_SECS   = 900  # 15-minute AIE window
BLINK_MIN_WINDOW_SECS = 30   # wait for enough observation time

# --- TAKE A BREAK INTERVENTION ---
BREAK_TRANSITIONS     = 3      
BREAK_WINDOW_SECS     = 300  # 5-minute window for frequent switches
# ---------------------------------

ALERT_COOLDOWN_SECS = 8      # seconds between repeat sound alerts

# ──────────────────────────────────────────────────────────────────────────────
# Sound alerts
# ──────────────────────────────────────────────────────────────────────────────

_ALERT_SOUNDS = {
    "FACE NOT FOUND":  [(440, 200), (440, 200)],
    "WARNING: DROWSY": [(300, 600), (300, 600)],
    "NOT FOCUSED":     [(880, 150), (880, 150), (880, 150)],
    "FATIGUED":        [(550, 400)],
    "POOR POSTURE":    [(660, 300), (500, 300)],
    "TAKE A BREAK":    [(550, 400), (440, 400)], # New specific sound pattern
}


def _play_sound(state: str) -> None:
    pattern = _ALERT_SOUNDS.get(state)
    if not pattern:
        return

    def _worker():
        try:
            import winsound
            for freq, dur in pattern:
                winsound.Beep(freq, dur)
                time.sleep(0.05)
        except ImportError:
            try:
                import subprocess, sys
                if sys.platform == "darwin":
                    subprocess.Popen(["say", state.lower()],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                else:
                    for _ in pattern:
                        print("\a", end="", flush=True)
                        time.sleep(0.25)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
# Landmark indices
# ──────────────────────────────────────────────────────────────────────────────

_L_EYE = [33,  160, 158, 133, 153, 144]
_R_EYE = [362, 385, 387, 263, 373, 380]

_FACE_3D = np.array([
    [ 0.0,    0.0,    0.0 ],   # nose tip
    [ 0.0,  -330.0,  -65.0],   # chin
    [-225.0,  170.0,-135.0],   # L eye left
    [ 225.0,  170.0,-135.0],   # R eye right
    [-150.0, -150.0,-125.0],   # L mouth
    [ 150.0, -150.0,-125.0],   # R mouth
], dtype=np.float64)
_FACE_2D_IDX = [1, 152, 263, 33, 287, 57]

_POSE_L_EAR      = 7
_POSE_R_EAR      = 8
_POSE_L_SHOULDER = 11
_POSE_R_SHOULDER = 12


# ──────────────────────────────────────────────────────────────────────────────
# BiometricEngine
# ──────────────────────────────────────────────────────────────────────────────

class BiometricEngine:
    def __init__(self) -> None:
        ensure_models()
        self.offset_yaw = 0.0
        self.offset_pitch = 0.0

        face_opts = mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(FACE_MODEL_PATH)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
        )
        self._face_det = mp_vision.FaceLandmarker.create_from_options(face_opts)

        pose_opts = mp_vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(POSE_MODEL_PATH)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
        )
        self._pose_det = mp_vision.PoseLandmarker.create_from_options(pose_opts)

        self.study_mins: int = 25
        self.break_mins: int = 10

        self._focus_records: list[int] = []
        self._transition_times: list[float] = []
        self._prev_focused: bool = True
        
        # UI Control Flags
        self.should_pause_timer: bool = False

        self._drowsy_frames:   int = 0
        self._distract_frames: int = 0
        self._posture_frames:  int = 0

        self._blink_times: deque = deque()
        self._prev_ear_closed: bool = False

        self.status: str = "Ready"
        self.last_ear: float = 0.3
        self.raw_metrics: dict = {
            "ear": 0.3, "yaw": 0.0, "pitch": 0.0,
            "blinks_per_min": 0, "slouch": False,
        }

        self._last_alert_time: float = 0.0
        self._last_alerted_state: str = ""

        self._frame_ts: int = 0
        self._session_start: float = time.time()

    def calibrate_center(self):
        self.offset_yaw += self.raw_metrics['yaw']
        self.offset_pitch += self.raw_metrics['pitch']
        self._distract_frames = 0
        self._posture_frames = 0

    def process_frame(self, frame: np.ndarray, active: bool) -> np.ndarray:
        if not active:
            self.status = "Paused"
            self._drowsy_frames = self._distract_frames = self._posture_frames = 0
            return frame

        h, w = frame.shape[:2]
        self._frame_ts += 33

        mp_img = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )

        face_res = self._face_det.detect_for_video(mp_img, self._frame_ts)
        pose_res = self._pose_det.detect_for_video(mp_img, self._frame_ts)

        if not face_res.face_landmarks:
            self._drowsy_frames = self._distract_frames = 0
            self._set_state("FACE NOT FOUND", focused=False)
            return frame

        lms = face_res.face_landmarks[0]

        ear         = self._calc_ear(lms, w, h)
        yaw, pitch  = self._head_pose(lms, w, h)
        bpm         = self._update_blinks(ear)
        slouch      = self._check_posture(pose_res, w, h)

        self.last_ear = ear
        self.raw_metrics = {
            "ear": round(ear, 3), "yaw": round(yaw, 1),
            "pitch": round(pitch, 1), "blinks_per_min": bpm,
            "slouch": slouch,
        }

        # 1. Drowsiness
        if ear < EAR_CLOSED_THRESH:
            self._drowsy_frames += 1
        else:
            self._drowsy_frames = max(0, self._drowsy_frames - 1)

        if self._drowsy_frames >= DROWSY_FRAMES:
            self._set_state("WARNING: DROWSY", focused=False)
            return frame

        # 2. Distraction
        looking_away = (abs(yaw) > GAZE_YAW_THRESH or abs(pitch) > GAZE_PITCH_THRESH)
        if looking_away:
            self._distract_frames += 1
        else:
            self._distract_frames = max(0, self._distract_frames - 2)

        if self._distract_frames >= DISTRACT_FRAMES:
            self._set_state("NOT FOCUSED", focused=False)
            return frame

        # 3. Fatigue
        now = time.time()
        # Clean transition list for the 15-minute window
        self._transition_times = [t for t in self._transition_times if now - t < FATIGUE_WINDOW_SECS]
        
        if len(self._transition_times) >= FATIGUE_TRANSITIONS or bpm >= HIGH_BLINK_RATE:
            self._set_state("FATIGUED", focused=False)
            return frame

        # 4. Posture
        if slouch:
            self._posture_frames += 1
        else:
            self._posture_frames = max(0, self._posture_frames - 1)

        if self._posture_frames >= POSTURE_FRAMES:
            self._set_state("POOR POSTURE", focused=True)
            return frame

        self._set_state("Focused", focused=True)
        return frame

    def _set_state(self, state: str, focused: bool) -> None:
        now = time.time()
        grace_elapsed = now - self._session_start
        
        # Monitor frequent state changes (3 switches in 5 mins)
        if self._prev_focused and not focused and grace_elapsed > 10.0:
            self._transition_times.append(now)
            
            recent_transitions = [t for t in self._transition_times if now - t < BREAK_WINDOW_SECS]
            
            if len(recent_transitions) >= BREAK_TRANSITIONS:
                self.status = "TAKE A BREAK"
                self.should_pause_timer = True
                _play_sound("TAKE A BREAK")
                return # Priority interrupt

        self._prev_focused = focused
        self.status = state
        self._focus_records.append(1 if focused else 0)

        is_warning = state not in ("Focused", "Paused", "Ready", "TAKE A BREAK")
        changed    = state != self._last_alerted_state
        cooled     = now - self._last_alert_time > ALERT_COOLDOWN_SECS

        if is_warning and (changed or cooled):
            _play_sound(state)
            self._last_alert_time    = now
            self._last_alerted_state = state

    def _calc_ear(self, lms, w: int, h: int) -> float:
        def _ear(idx):
            pts = [np.array([lms[i].x * w, lms[i].y * h]) for i in idx]
            v1 = dist.euclidean(pts[1], pts[5])
            v2 = dist.euclidean(pts[2], pts[4])
            h1 = dist.euclidean(pts[0], pts[3])
            return (v1 + v2) / (2.0 * h1) if h1 else 0.3
        return (_ear(_L_EYE) + _ear(_R_EYE)) / 2.0

    def _update_blinks(self, ear: float) -> int:
        now = time.time()
        closed = ear < EAR_CLOSED_THRESH
        if self._prev_ear_closed and not closed:
            self._blink_times.append(now)
        self._prev_ear_closed = closed

        cutoff = now - BLINK_WINDOW_SECS
        while self._blink_times and self._blink_times[0] < cutoff:
            self._blink_times.popleft()

        if not self._blink_times: return 0
        session_elapsed = now - self._session_start
        if session_elapsed < BLINK_MIN_WINDOW_SECS: return 0
        elapsed = min(now - self._blink_times[0], BLINK_WINDOW_SECS)
        if elapsed < 10: return 0
        return int(len(self._blink_times) / elapsed * 60)

    def _head_pose(self, lms, w: int, h: int) -> tuple:
        pts2d = np.array([[lms[i].x * w, lms[i].y * h] for i in _FACE_2D_IDX], dtype=np.float64)
        focal = float(w)
        cam   = np.array([[focal, 0, w/2], [0, focal, h/2], [0, 0, 1]], dtype=np.float64)
        dc    = np.zeros((4, 1), dtype=np.float64)

        ok, rvec, _ = cv2.solvePnP(_FACE_3D, pts2d, cam, dc, flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok: return 0.0, 0.0

        rmat, _ = cv2.Rodrigues(rvec)
        sy = math.sqrt(rmat[0, 0]**2 + rmat[1, 0]**2)
        
        if sy > 1e-6:
            pitch, yaw = math.atan2(-rmat[2, 0], sy), math.atan2( rmat[1, 0], rmat[0, 0])
        else:
            pitch, yaw = math.atan2(-rmat[2, 0], sy), 0.0

        y_deg, p_deg = math.degrees(yaw), math.degrees(pitch)
        if y_deg > 90: y_deg -= 180
        if y_deg < -90: y_deg += 180

        return y_deg - self.offset_yaw, p_deg - self.offset_pitch

    def _check_posture(self, pose_res, w: int, h: int) -> bool:
        if not pose_res.pose_landmarks: return False
        plms = pose_res.pose_landmarks[0]
        ear_y  = (plms[_POSE_L_EAR].y + plms[_POSE_R_EAR].y) / 2 * h
        sh_y   = (plms[_POSE_L_SHOULDER].y + plms[_POSE_R_SHOULDER].y) / 2 * h
        sh_w   = abs(plms[_POSE_L_SHOULDER].x - plms[_POSE_R_SHOULDER].x) * w
        if sh_w < 1: return False
        return ((sh_y - ear_y) / sh_w) < SLOUCH_RATIO_THRESH

    def update_ml_plan(self) -> float:
        score = self.focus_score()
        if score < 75:
            self.study_mins = max(15, self.study_mins - 5)
            self.break_mins = min(20, self.break_mins + 2)
        elif score > 92:
            self.study_mins = min(50, self.study_mins + 5)
            self.break_mins = max(5,  self.break_mins - 1)
        self.reset_records()
        return score

    def reset_records(self) -> None:
        self._focus_records.clear()
        self._transition_times.clear()
        self._blink_times.clear()
        self._session_start = time.time()

    def focus_score(self) -> float:
        if not self._focus_records: return 0.0
        return sum(self._focus_records) / len(self._focus_records) * 100

# ──────────────────────────────────────────────────────────────────────────────
# HUD overlay
# ──────────────────────────────────────────────────────────────────────────────

_STATE_COLORS = {
    "Focused":         (16,  185, 129),
    "POOR POSTURE":    (245, 158,  11),
    "NOT FOCUSED":     (239,  68,  68),
    "WARNING: DROWSY": (239,  68,  68),
    "FATIGUED":        (239,  68,  68),
    "TAKE A BREAK":    (239,  68,  68),
    "FACE NOT FOUND":  (148, 163, 184),
    "Paused":          (148, 163, 184),
}

def draw_status_overlay(frame: np.ndarray, engine: "BiometricEngine") -> np.ndarray:
    status, metrics, color = engine.status, engine.raw_metrics, _STATE_COLORS.get(engine.status, (239, 68, 68))
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], 70), (10, 12, 28), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(frame, status, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
    info = (f"EAR:{metrics['ear']:.2f}  Yaw:{metrics['yaw']:+.0f}deg  "
            f"Pitch:{metrics['pitch']:+.0f}deg  Blink:{metrics['blinks_per_min']}/min")
    cv2.putText(frame, info, (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 190, 210), 1, cv2.LINE_AA)
    return frame