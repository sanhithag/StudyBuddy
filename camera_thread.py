"""
camera_thread.py — StudyBuddy AI
QThread that captures webcam frames and passes them to the BiometricEngine.
Separated from pages.py so the threading concern is isolated.
"""

import time
import numpy as np

import cv2
from PyQt6.QtCore import QThread, pyqtSignal

from biometric import BiometricEngine, draw_status_overlay  # type: ignore


class CameraThread(QThread):
    """
    Runs continuously. Emits `frame_ready` with every processed frame.
    `active` controls whether the engine actually analyses focus.
    """

    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, engine: BiometricEngine, cam_index: int = 0) -> None:
        super().__init__()
        self.engine    = engine
        self.cam_index = cam_index
        self.active    = False
        self._running  = True

    def run(self) -> None:
        cap = cv2.VideoCapture(self.cam_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

        while self._running:
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                frame = self.engine.process_frame(frame, self.active)
                frame = draw_status_overlay(frame, self.engine)
                self.frame_ready.emit(frame)
            time.sleep(0.033)   # ~30 fps

        cap.release()

    def stop(self) -> None:
        self._running = False
        self.wait()