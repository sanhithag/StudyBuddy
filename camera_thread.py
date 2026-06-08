"""
MODULE PURPOSE

Provides a dedicated camera-processing thread for StudyBuddy AI.

This module separates webcam capture and biometric analysis from the main UI
thread, ensuring smooth application performance and preventing interface
freezing during continuous video processing.

MAIN RESPONSIBILITIES
Initialize and warm up the webcam.
Capture live video frames.
Pass frames to the biometric engine.
Render biometric status overlays.
Emit processed frames back to the UI.
Maintain real-time performance using a dedicated QThread.
"""
import sys
import threading
import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from biometric import BiometricEngine, draw_status_overlay  # type: ignore

# Number of dummy frames to discard during warm-up; most webcam drivers
# return black / corrupted frames for the first few reads.
_WARMUP_FRAMES = 5


def _open_capture(cam_index: int) -> cv2.VideoCapture:
    """
    Open a VideoCapture using the best available backend for the current OS.

    CAP_DSHOW is Windows-only and causes errors or silent failures on
    Linux / macOS.  On those platforms we fall back to the default backend
    (CAP_ANY = 0), which lets OpenCV pick the right one automatically.
    """
    if sys.platform == "win32":
        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(cam_index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)   # minimise latency
    return cap


class CameraThread(QThread):
    """
    Continuous webcam processing thread.

    Emits:
        frame_ready(np.ndarray)

    Attributes:
        active:
            Controls whether biometric analysis is enabled.

        _running:
            Controls thread execution.

        _cap:
            Shared VideoCapture instance.

        _cap_ready:
            Signals when camera warm-up is complete.
    """

    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, engine: BiometricEngine, cam_index: int = 0) -> None:
        super().__init__()
        self.engine    = engine
        self.cam_index = cam_index
        self.active    = False
        self._running  = True

        # The capture object and a ready-event are shared between the
        # pre-warm thread and run().
        self._cap: cv2.VideoCapture | None = None
        self._cap_ready = threading.Event()

        # Start the warm-up immediately so the delay is hidden behind the
        # Session Select page UI.
        self._prewarm_thread = threading.Thread(
            target=self._prewarm, daemon=True, name="cam-prewarm"
        )
        self._prewarm_thread.start()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _prewarm(self) -> None:
        """Open the camera and discard a few startup frames, then signal ready."""
        cap = _open_capture(self.cam_index)

        # Discard the first few frames that many drivers return as black/corrupt
        for _ in range(_WARMUP_FRAMES):
            cap.read()

        self._cap = cap
        self._cap_ready.set()

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        # Wait for the pre-warm to finish (should already be done, but
        # guard against the case where the user clicks Start very quickly).
        self._cap_ready.wait(timeout=10.0)

        cap = self._cap
        if cap is None or not cap.isOpened():
            # Fallback: open synchronously if pre-warm somehow failed
            cap = _open_capture(self.cam_index)

        while self._running:
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                frame = self.engine.process_frame(frame, self.active)
                frame = draw_status_overlay(frame, self.engine)
                self.frame_ready.emit(frame)
            time.sleep(0.033)   # ~30 fps

        cap.release()
        self._cap = None

    def stop(self) -> None:
        self._running = False
        # Unblock run() if it is still waiting on the pre-warm event so that
        # teardown completes immediately rather than after a 10-second timeout.
        self._cap_ready.set()
        self.wait()

    def restart(self) -> None:
        """Re-enable processing and start the thread if it is not already running."""
        self._running = True
        if not self.isRunning():
            self.start()