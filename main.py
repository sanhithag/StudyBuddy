"""
main.py — StudyBuddy AI
Entry point. Instantiates MainApp and starts the Qt event loop.

Run:
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt

import storage
from biometric import BiometricEngine
from camera_thread import CameraThread
from theme import STYLESHEET
from pages import (
    LoginPage, RegisterPage, ForgotPasswordPage,
    ProfilePage, StatsPage, SettingsPage, WorkspacePage,
)


class MainApp(QMainWindow):
    """
    Owns the QStackedWidget (router) and all page instances.
    Pages communicate back via signals; this class does the routing.
    """

    # Page indices in the stack
    _IDX_LOGIN    = 0
    _IDX_REGISTER = 1
    _IDX_FORGOT   = 2
    # Workspace and beyond are created dynamically per-user

    def __init__(self) -> None:
        super().__init__()
        storage.init_db()

        self.setWindowTitle("StudyBuddy AI")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumSize(960, 780)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # ── Pre-auth pages (always present) ──
        self._login_pg    = LoginPage()
        self._register_pg = RegisterPage()
        self._forgot_pg   = ForgotPasswordPage()

        self._stack.addWidget(self._login_pg)    # 0
        self._stack.addWidget(self._register_pg) # 1
        self._stack.addWidget(self._forgot_pg)   # 2

        # Wire auth flow
        self._login_pg.sig_logged_in.connect(self._on_login)
        self._login_pg.sig_go_register.connect(lambda: self._show(self._IDX_REGISTER))
        self._login_pg.sig_go_forgot.connect(lambda: self._show(self._IDX_FORGOT))

        self._register_pg.sig_registered.connect(self._on_login)
        self._register_pg.sig_go_login.connect(lambda: self._show(self._IDX_LOGIN))

        self._forgot_pg.sig_go_login.connect(lambda: self._show(self._IDX_LOGIN))

        # ML / camera (created once, reused across sessions)
        self._engine: BiometricEngine | None = None
        self._cam_thread: CameraThread | None = None

        self._show(self._IDX_LOGIN)

    # ──────────────────────────────────────────
    # Auth events
    # ──────────────────────────────────────────

    def _on_login(self, username: str) -> None:
        self._username = username
        self._build_workspace(username)

    def _on_logout(self) -> None:
        """Stop camera, tear down user pages, go back to login."""
        if self._cam_thread:
            self._cam_thread.stop()
            self._cam_thread = None

        # Remove all dynamic pages (indices ≥ 3)
        while self._stack.count() > 3:
            w = self._stack.widget(3)
            self._stack.removeWidget(w)
            w.deleteLater()

        self._engine = None
        self._show(self._IDX_LOGIN)

    # ──────────────────────────────────────────
    # Workspace setup
    # ──────────────────────────────────────────

    def _build_workspace(self, username: str) -> None:
        """Create per-user pages and start camera."""
        self._engine = BiometricEngine()
        self._cam_thread = CameraThread(self._engine)

        self._workspace_pg = WorkspacePage(username, self._engine)
        self._profile_pg   = ProfilePage(username)
        self._stats_pg     = StatsPage(username)
        self._settings_pg  = SettingsPage(username)

        for pg in [self._workspace_pg, self._profile_pg,
                   self._stats_pg, self._settings_pg]:
            self._stack.addWidget(pg)

        # Workspace navigation signals
        self._workspace_pg.sig_show_stats.connect(self._show_stats)
        self._workspace_pg.sig_show_profile.connect(self._show_profile)
        self._workspace_pg.sig_show_settings.connect(self._show_settings)

        # Profile signals
        self._profile_pg.sig_back.connect(self._show_workspace)
        self._profile_pg.sig_logout.connect(self._on_logout)

        # Stats signals
        self._stats_pg.sig_back.connect(self._show_workspace)

        # Settings signals
        self._settings_pg.sig_back.connect(self._show_workspace)
        self._settings_pg.sig_logout.connect(self._on_logout)
        self._settings_pg.sig_account_deleted.connect(self._on_logout)

        # Camera → workspace frame display
        self._cam_thread.frame_ready.connect(
            lambda f: (
                self._workspace_pg.update_frame(f)
                if self._cam_thread else None
            )
        )
        # Sync camera active flag with workspace
        # (polled via a simple property check every frame)
        self._cam_thread.frame_ready.connect(self._sync_cam_active)

        self._cam_thread.start()
        self._show_workspace()

    def _sync_cam_active(self, _frame) -> None:
        if self._cam_thread:
            self._cam_thread.active = self._workspace_pg.is_active

    # ──────────────────────────────────────────
    # Page navigation helpers
    # ──────────────────────────────────────────

    def _show(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)

    def _show_workspace(self) -> None:
        self._stack.setCurrentWidget(self._workspace_pg)
        self._workspace_pg.refresh_plan()

    def _show_profile(self) -> None:
        # Rebuild profile page to reflect latest DB state
        self._stack.removeWidget(self._profile_pg)
        self._profile_pg.deleteLater()
        self._profile_pg = ProfilePage(self._username)
        self._profile_pg.sig_back.connect(self._show_workspace)
        self._profile_pg.sig_logout.connect(self._on_logout)
        self._stack.addWidget(self._profile_pg)
        self._stack.setCurrentWidget(self._profile_pg)

    def _show_stats(self) -> None:
        # Rebuild to fetch latest data
        self._stack.removeWidget(self._stats_pg)
        self._stats_pg.deleteLater()
        self._stats_pg = StatsPage(self._username)
        self._stats_pg.sig_back.connect(self._show_workspace)
        self._stack.addWidget(self._stats_pg)
        self._stack.setCurrentWidget(self._stats_pg)

    def _show_settings(self) -> None:
        self._stack.setCurrentWidget(self._settings_pg)

    # ──────────────────────────────────────────
    # Cleanup on close
    # ──────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._cam_thread:
            self._cam_thread.stop()
        event.accept()


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("StudyBuddy AI")
    win = MainApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
