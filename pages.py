"""
===============================================================================
FILE: pages.py
===============================================================================

MODULE PURPOSE
--------------
Contains all user interface pages used throughout StudyBuddy.

PAGES INCLUDED
--------------
1. LoginPage
2. RegisterPage
3. ForgotPasswordPage
4. ProfilePage
5. StatsPage
6. SettingsPage
7. WorkspacePage
8. SessionSelectPage
9. BreakDialog

UI RESPONSIBILITIES
-------------------
• Authentication
• User Profile Management
• Session Selection
• Study Workspace
• Statistics Dashboard
• Application Settings
• Break Management

WORKFLOW
--------
Login
  ↓
Session Selection
  ↓
Workspace
  ↓
Break Suggestions
  ↓
Statistics & Analytics
  ↓
Profile / Settings

DEPENDENCIES
------------
- PyQt6
- storage.py
- theme.py
- widgets.py
- biometric.py

===============================================================================
"""

import datetime
import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QFrame,
    QScrollArea, QDoubleSpinBox, QComboBox, QGridLayout,
    QSizePolicy, QDialog, QSpinBox, QApplication, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage

import cv2
import numpy as np

import storage
from biometric import BREAK_TRANSITIONS, BREAK_WINDOW_SECS
from theme import PALETTE, AVATAR_COLORS
from widgets import HDivider, StatCard, AvatarCircle, ColorPickerRow, MessageBanner


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _label(text, obj_name="", bold=False, size=14):
    lbl = QLabel(text)
    if obj_name:
        lbl.setObjectName(obj_name)
    if bold:
        lbl.setFont(QFont("Segoe UI", size, QFont.Weight.Bold))
    return lbl


def _field(placeholder="", password=False):
    f = QLineEdit()
    f.setPlaceholderText(placeholder)
    if password:
        f.setEchoMode(QLineEdit.EchoMode.Password)
    return f


def _btn(text, obj_name="", fixed_w=None):
    b = QPushButton(text)
    if obj_name:
        b.setObjectName(obj_name)
    if fixed_w:
        b.setFixedWidth(fixed_w)
    return b


def _back_btn(label="← Back"):
    """Consistent styled back button used across all pages."""
    b = QPushButton(label)
    b.setObjectName("btn_secondary")
    b.setFixedHeight(32)
    b.setMinimumWidth(90)
    b.setStyleSheet(
        f"font-size:14px; font-weight:600; background:{PALETTE['bg_panel']};"
        f"border:1px solid {PALETTE['border']}; border-radius:8px;"
        f"color:{PALETTE['text_hi']}; padding: 0 14px;"
    )
    return b


# ──────────────────────────────────────────────
# LOGIN PAGE
# ──────────────────────────────────────────────

class LoginPage(QWidget):
    sig_logged_in   = pyqtSignal(str)
    sig_go_register = pyqtSignal()
    sig_go_forgot   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame(); box.setObjectName("card"); box.setFixedWidth(400)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(36, 36, 36, 36); layout.setSpacing(14)

        logo = _label("StudyBuddy", "label_heading", bold=True, size=28)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = _label("A calmer way to stay focused.", "label_subheading")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.user   = _field("Username")
        self.pwd    = _field("Password", password=True)
        self.banner = MessageBanner()

        btn_login = _btn("LOG IN")
        btn_login.clicked.connect(self._login)

        row = QHBoxLayout()
        btn_reg    = _btn("Create account", "btn_ghost")
        btn_forgot = _btn("Forgot password?", "btn_ghost")
        btn_reg.clicked.connect(self.sig_go_register.emit)
        btn_forgot.clicked.connect(self.sig_go_forgot.emit)
        row.addWidget(btn_reg); row.addStretch(); row.addWidget(btn_forgot)

        for w in [logo, sub, HDivider(), self.user, self.pwd, self.banner, btn_login]:
            layout.addWidget(w)
        layout.addLayout(row)
        outer.addWidget(box, alignment=Qt.AlignmentFlag.AlignCenter)

    def _login(self):
        u, p = self.user.text().strip(), self.pwd.text()
        if not u or not p:
            self.banner.show_error("Please fill in all fields.")
            return
        ok, msg = storage.verify_login(u, p)
        if ok:
            self.banner.clear()
            self.user.clear(); self.pwd.clear()
            storage.save_session_token(u)
            self.sig_logged_in.emit(u)
        else:
            self.banner.show_error(msg)


# ──────────────────────────────────────────────
# REGISTER PAGE
# ──────────────────────────────────────────────

class RegisterPage(QWidget):
    sig_registered = pyqtSignal(str)
    sig_go_login   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self); outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame(); box.setObjectName("card"); box.setFixedWidth(440)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(36, 36, 36, 36); layout.setSpacing(12)

        layout.addWidget(_label("Create Account", "label_heading", bold=True))
        layout.addWidget(HDivider())

        self.full_name = _field("Full name")
        self.email     = _field("Email (optional)")
        self.user      = _field("Username")
        self.pwd       = _field("Password", password=True)
        self.pwd2      = _field("Confirm password", password=True)

        layout.addWidget(_label("Security question (for password recovery)"))
        self.q_combo = QComboBox(); self.q_combo.addItems(storage.SECURITY_QUESTIONS)
        self.sec_ans = _field("Your answer")

        self.banner = MessageBanner()
        btn_reg  = _btn("CREATE ACCOUNT")
        btn_reg.clicked.connect(self._register)
        btn_back = _back_btn("← Back to login")
        btn_back.clicked.connect(self.sig_go_login.emit)

        for w in [self.full_name, self.email, HDivider(),
                  self.user, self.pwd, self.pwd2, HDivider(),
                  self.q_combo, self.sec_ans, self.banner, btn_reg, btn_back]:
            layout.addWidget(w)
        outer.addWidget(box, alignment=Qt.AlignmentFlag.AlignCenter)

    def _register(self):
        fn  = self.full_name.text().strip(); em  = self.email.text().strip()
        u   = self.user.text().strip();      p   = self.pwd.text()
        p2  = self.pwd2.text();              q   = self.q_combo.currentText()
        ans = self.sec_ans.text().strip()

        if not u or not p:
            self.banner.show_error("Username and password are required."); return
        if p != p2:
            self.banner.show_error("Passwords do not match."); return
        if len(p) < 6:
            self.banner.show_error("Password must be at least 6 characters."); return
        if not ans:
            self.banner.show_error("Please provide a security answer."); return

        ok, msg = storage.register_user(u, p, fn, em)
        if not ok:
            self.banner.show_error(msg); return
        storage.set_security_question(u, q, ans)
        self.banner.show_success("Account created! Logging you in…")
        storage.save_session_token(u)
        QTimer.singleShot(800, lambda: self.sig_registered.emit(u))


# ──────────────────────────────────────────────
# FORGOT PASSWORD PAGE
# ──────────────────────────────────────────────

class ForgotPasswordPage(QWidget):
    sig_go_login = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self); outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame(); box.setObjectName("card"); box.setFixedWidth(420)
        self._layout = QVBoxLayout(box)
        self._layout.setContentsMargins(36, 36, 36, 36); self._layout.setSpacing(12)

        self._step1 = QWidget()
        l1 = QVBoxLayout(self._step1); l1.setContentsMargins(0,0,0,0); l1.setSpacing(12)
        l1.addWidget(_label("Forgot Password", "label_heading", bold=True))
        l1.addWidget(_label("Enter your username to find your account.", "label_subheading"))
        l1.addWidget(HDivider())
        self.user_input = _field("Username")
        self.banner1    = MessageBanner()
        btn_next = _btn("FIND ACCOUNT"); btn_next.clicked.connect(self._find_account)
        btn_back = _back_btn("← Back to login"); btn_back.clicked.connect(self.sig_go_login.emit)
        for w in [self.user_input, self.banner1, btn_next, btn_back]: l1.addWidget(w)

        self._step2 = QWidget()
        l2 = QVBoxLayout(self._step2); l2.setContentsMargins(0,0,0,0); l2.setSpacing(12)
        self.q_label  = _label("", "label_subheading"); self.q_label.setWordWrap(True)
        self.ans_input = _field("Your answer")
        self.new_pwd   = _field("New password", password=True)
        self.new_pwd2  = _field("Confirm new password", password=True)
        self.banner2   = MessageBanner()
        btn_reset = _btn("RESET PASSWORD"); btn_reset.clicked.connect(self._reset)
        for w in [_label("Answer your security question","label_heading",bold=True),
                  HDivider(), self.q_label, self.ans_input,
                  self.new_pwd, self.new_pwd2, self.banner2, btn_reset]:
            l2.addWidget(w)

        self._layout.addWidget(self._step1)
        self._layout.addWidget(self._step2)
        self._step2.hide()
        outer.addWidget(box, alignment=Qt.AlignmentFlag.AlignCenter)

    def _find_account(self):
        u = self.user_input.text().strip()
        q = storage.get_security_question(u)
        if not q:
            self.banner1.show_error("Username not found or no security question set."); return
        self._username = u
        self.q_label.setText(f"❓  {q}")
        self._step1.hide(); self._step2.show()

    def _reset(self):
        ans = self.ans_input.text().strip(); np_ = self.new_pwd.text(); np2 = self.new_pwd2.text()
        if np_ != np2:   self.banner2.show_error("Passwords do not match."); return
        if len(np_) < 6: self.banner2.show_error("Password must be at least 6 characters."); return
        ok, msg = storage.reset_password_via_security(self._username, ans, np_)
        if ok:
            self.banner2.show_success(msg + " Redirecting…")
            QTimer.singleShot(1200, self.sig_go_login.emit)
        else:
            self.banner2.show_error(msg)


# ──────────────────────────────────────────────
# PROFILE PAGE
# ──────────────────────────────────────────────

class ProfilePage(QWidget):
    sig_back   = pyqtSignal()
    sig_logout = pyqtSignal()

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self._username = username
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(40, 30, 40, 30); main.setSpacing(20)

        hdr = QHBoxLayout()
        btn_back = _back_btn("← Back")
        btn_back.clicked.connect(self.sig_back.emit)
        hdr.addWidget(btn_back); hdr.addStretch()
        btn_logout = _btn("LOG OUT", "btn_danger", fixed_w=120)
        btn_logout.setMinimumHeight(38)
        btn_logout.clicked.connect(self._logout)
        hdr.addWidget(btn_logout)
        main.addLayout(hdr)

        prof     = storage.get_profile(username) or {}
        initials = (prof.get("full_name") or username)[:2].upper()
        color    = prof.get("avatar_color", AVATAR_COLORS[0])

        top_card = QFrame(); top_card.setObjectName("card")
        top_row  = QHBoxLayout(top_card)
        top_row.setContentsMargins(24, 20, 24, 20); top_row.setSpacing(20)

        self._avatar = AvatarCircle(initials, color, 72)
        top_row.addWidget(self._avatar)

        name_col = QVBoxLayout(); name_col.setSpacing(4)
        self._name_lbl = _label(prof.get("full_name") or username, bold=True, size=19)
        self._name_lbl.setFont(QFont("Segoe UI", 19, QFont.Weight.Bold))
        self._username_lbl = _label(f"@{username}", "label_muted")
        self._since_lbl    = _label(f"Member since {prof.get('created_at','—')}", "label_muted")
        name_col.addWidget(self._name_lbl)
        name_col.addWidget(self._username_lbl)
        name_col.addWidget(self._since_lbl)
        top_row.addLayout(name_col); top_row.addStretch()
        main.addWidget(top_card)

        form_card = QFrame(); form_card.setObjectName("card")
        fl = QVBoxLayout(form_card)
        fl.setContentsMargins(24, 20, 24, 20); fl.setSpacing(10)
        fl.addWidget(_label("EDIT PROFILE", "label_muted")); fl.addWidget(HDivider())

        self.f_name  = _field("Full name");  self.f_name.setText(prof.get("full_name",""))
        self.f_email = _field("Email");      self.f_email.setText(prof.get("email",""))
        fl.addWidget(_label("Full name"));   fl.addWidget(self.f_name)
        fl.addWidget(_label("Email"));       fl.addWidget(self.f_email)
        fl.addWidget(_label("Daily study goal (hours)"))
        self.f_goal = QDoubleSpinBox()
        self.f_goal.setRange(0.5, 12.0); self.f_goal.setSingleStep(0.5)
        self.f_goal.setValue(prof.get("study_goal_hrs", 2.0))
        fl.addWidget(self.f_goal)
        fl.addWidget(_label("Avatar colour"))
        self._color_picker = ColorPickerRow(AVATAR_COLORS, color)
        self._color_picker.color_selected.connect(self._preview_color)
        fl.addWidget(self._color_picker)
        self.prof_banner = MessageBanner()
        btn_save = _btn("SAVE CHANGES"); btn_save.clicked.connect(self._save_profile)
        fl.addWidget(self.prof_banner); fl.addWidget(btn_save)
        main.addWidget(form_card)

        pw_card = QFrame(); pw_card.setObjectName("card")
        pl = QVBoxLayout(pw_card)
        pl.setContentsMargins(24, 20, 24, 20); pl.setSpacing(10)
        pl.addWidget(_label("CHANGE PASSWORD", "label_muted")); pl.addWidget(HDivider())
        self.pw_old  = _field("Current password",  password=True)
        self.pw_new  = _field("New password",       password=True)
        self.pw_new2 = _field("Confirm new password", password=True)
        self.pw_banner = MessageBanner()
        btn_pw = _btn("UPDATE PASSWORD"); btn_pw.clicked.connect(self._change_password)
        for w in [self.pw_old, self.pw_new, self.pw_new2, self.pw_banner, btn_pw]:
            pl.addWidget(w)
        main.addWidget(pw_card)
        main.addStretch()
        scroll.setWidget(container)
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.addWidget(scroll)

    def _preview_color(self, color: str) -> None:
        fn = self.f_name.text().strip() or self._username
        self._avatar.set_color(color); self._avatar.set_initials(fn[:2])

    def _save_profile(self) -> None:
        fn=self.f_name.text().strip(); em=self.f_email.text().strip()
        goal=self.f_goal.value(); color=self._color_picker.current_color()
        ok,msg=storage.update_profile(self._username,fn,em,goal,color)
        if ok:
            self.prof_banner.show_success(msg)
            self._name_lbl.setText(fn or self._username)
            self._avatar.set_initials((fn or self._username)[:2])
            self._avatar.set_color(color)
        else:
            self.prof_banner.show_error(msg)

    def _change_password(self) -> None:
        old=self.pw_old.text(); new=self.pw_new.text(); c=self.pw_new2.text()
        if new!=c:     self.pw_banner.show_error("New passwords do not match."); return
        if len(new)<6: self.pw_banner.show_error("Password must be ≥ 6 characters."); return
        ok,msg=storage.change_password(self._username,old,new)
        if ok:
            self.pw_banner.show_success(msg)
            self.pw_old.clear(); self.pw_new.clear(); self.pw_new2.clear()
        else:
            self.pw_banner.show_error(msg)

    def _logout(self) -> None:
        storage.clear_session_token(); self.sig_logout.emit()

    def refresh(self) -> None:
        """Reload profile data from the DB and update all displayed fields."""
        prof = storage.get_profile(self._username) or {}
        fn    = prof.get("full_name") or self._username
        color = prof.get("avatar_color", AVATAR_COLORS[0])

        self._name_lbl.setText(fn)
        self._avatar.set_initials(fn[:2])
        self._avatar.set_color(color)
        self.f_name.setText(prof.get("full_name", ""))
        self.f_email.setText(prof.get("email", ""))
        self.f_goal.setValue(prof.get("study_goal_hrs", 2.0))
        self._color_picker._pick(color)
        self.prof_banner.clear()
        self.pw_banner.clear()


# ──────────────────────────────────────────────
# STATS PAGE
# ──────────────────────────────────────────────

class StatsPage(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self._username = username
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(40,30,40,30); main.setSpacing(20)

        hdr = QHBoxLayout()
        hdr.addWidget(_label("Progress & Insights","label_heading",bold=True,size=23))
        hdr.addStretch()
        btn_back = _back_btn("← Back"); btn_back.clicked.connect(self.sig_back.emit)
        hdr.addWidget(btn_back)
        main.addLayout(hdr)

        summary = storage.get_stats_summary(username)
        grid    = QGridLayout(); grid.setSpacing(12)
        cards   = [
            StatCard("Sessions",    str(summary.get("total_sessions") or 0)),
            StatCard("Avg Focus",   f"{summary.get('avg_focus') or 0:.1f}", "%"),
            StatCard("Study Time",  str(int((summary.get('total_study_mins') or 0)/60)), "hrs"),
            StatCard("Active Days", str(summary.get("days_active_week") or 0), "/ wk"),
        ]
        for i,c in enumerate(cards): grid.addWidget(c,0,i)
        main.addLayout(grid)

        score = summary.get("avg_focus") or 0
        if score>90:   tip="You are in flow! Try advanced topic interleaving for maximum retention."
        elif score>70: tip="Solid focus. Apply the 2-minute rule to crush distractions before they snowball."
        elif score>0:  tip="Low focus detected. Consider 15-minute micro-burst sessions with active recall breaks."
        else:          tip="No sessions yet. Start your first session to get personalised coaching insights."

        tip_frame=QFrame(); tip_frame.setObjectName("card")
        tl=QVBoxLayout(tip_frame); tl.setContentsMargins(20,14,20,14)
        coach=QLabel(f"TODAY'S INSIGHT 🌱  —  {tip}"); coach.setWordWrap(True)
        coach.setStyleSheet(f"color:{PALETTE['text_hi']}; border-left:3px solid {PALETTE['accent']}; padding-left:12px;")
        tl.addWidget(coach); main.addWidget(tip_frame)

        main.addWidget(_label("RECENT SESSIONS","label_muted"))
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(["Date","Focus %","Study (min)","Break (min)","Notes"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(self.table.styleSheet()+f"alternate-background-color: rgba(255,255,255,0.03);")
        self._load_table(); main.addWidget(self.table)
        main.addStretch(); scroll.setWidget(container)
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.addWidget(scroll)

    def _load_table(self):
        rows=storage.get_recent_sessions(self._username,10)
        self.table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=[row["date"],f"{row['focus_score']:.1f}",str(row["study_mins"]),str(row["break_mins"]),row.get("notes","")]
            for c,v in enumerate(vals):
                item=QTableWidgetItem(v); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r,c,item)

    def refresh(self) -> None:
        """Reload the session table from the DB."""
        self._load_table()


# ──────────────────────────────────────────────
# SETTINGS PAGE
# ──────────────────────────────────────────────

class SettingsPage(QWidget):
    sig_back            = pyqtSignal()
    sig_logout          = pyqtSignal()
    sig_account_deleted = pyqtSignal()

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self._username = username
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(40,30,40,30); main.setSpacing(20)

        hdr = QHBoxLayout()
        hdr.addWidget(_label("Settings","label_heading",bold=True,size=23)); hdr.addStretch()
        btn_back = _back_btn("← Back"); btn_back.clicked.connect(self.sig_back.emit)
        hdr.addWidget(btn_back); main.addLayout(hdr)

        sq_card=QFrame(); sq_card.setObjectName("card")
        sql=QVBoxLayout(sq_card); sql.setContentsMargins(24,20,24,20); sql.setSpacing(10)
        sql.addWidget(_label("UPDATE SECURITY QUESTION","label_muted")); sql.addWidget(HDivider())
        self.sq_combo=QComboBox(); self.sq_combo.addItems(storage.SECURITY_QUESTIONS)
        self.sq_ans=_field("New answer"); self.sq_banner=MessageBanner()
        btn_sq=_btn("SAVE QUESTION"); btn_sq.clicked.connect(self._update_sq)
        for w in [self.sq_combo,self.sq_ans,self.sq_banner,btn_sq]: sql.addWidget(w)
        main.addWidget(sq_card)

        data_card=QFrame(); data_card.setObjectName("card")
        dl=QVBoxLayout(data_card); dl.setContentsMargins(24,20,24,20); dl.setSpacing(10)
        dl.addWidget(_label("DATA MANAGEMENT","label_muted")); dl.addWidget(HDivider())
        self.data_banner=MessageBanner()
        btn_wipe=_btn("WIPE SESSION HISTORY","btn_secondary"); btn_wipe.clicked.connect(self._wipe_history)
        btn_del=_btn("DELETE ACCOUNT","btn_danger"); btn_del.clicked.connect(self._delete_account)
        dl.addWidget(QLabel("Wipe all session history (account remains), or permanently delete your account."))
        dl.addWidget(self.data_banner); dl.addWidget(btn_wipe); dl.addWidget(btn_del)
        main.addWidget(data_card)
        main.addStretch(); scroll.setWidget(container)
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.addWidget(scroll)

    def _update_sq(self):
        ans=self.sq_ans.text().strip()
        if not ans: self.sq_banner.show_error("Answer cannot be empty."); return
        storage.set_security_question(self._username,self.sq_combo.currentText(),ans)
        self.sq_banner.show_success("Security question updated.")

    def _wipe_history(self):
        reply = QMessageBox.question(
            self, "Wipe History",
            "Are you sure you want to delete all session history? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            storage.delete_all_sessions(self._username)
            self.data_banner.show_success("All session history wiped.")
        except Exception as e:
            self.data_banner.show_error(f"Failed to wipe history: {e}")

    def _delete_account(self):
        reply = QMessageBox.warning(
            self, "Delete Account",
            "This will permanently delete your account and all data. "
            "This action cannot be undone.\n\nAre you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            storage.delete_account(self._username)
            self.sig_account_deleted.emit()
        except Exception as e:
            self.data_banner.show_error(f"Failed to delete account: {e}")


# ──────────────────────────────────────────────
# WORKSPACE PAGE
# ──────────────────────────────────────────────

BREAK_QUOTES = [
    "Take a deep breath and stretch. A quick rest keeps the mind sharp!",
    "Rest is part of the work. Breathe in, breathe out.",
    "Stand up, look at something distant, and let your eyes relax.",
    "Great progress so far! Rehydrate and refresh your mind.",
    "Breathe. Relax. Re-energize. You're doing amazing!",
    "Close your eyes for 20 seconds — your future self will thank you.",
    "Hydration check! Go grab some water.",
    "Roll your shoulders back. You've earned this moment.",
]

# How many focus→unfocused transitions in BREAK_WINDOW_SECS before
# we suggest a break (imported from biometric to stay in sync).
_BREAK_TRANSITIONS  = BREAK_TRANSITIONS
_BREAK_CHECK_WINDOW = BREAK_WINDOW_SECS


class WorkspacePage(QWidget):
    sig_show_stats    = pyqtSignal()
    sig_show_profile  = pyqtSignal()
    sig_show_settings = pyqtSignal()
    sig_session_ended  = pyqtSignal()
    sig_session_started = pyqtSignal()
    sig_session_paused  = pyqtSignal()

    def __init__(self, username: str, engine, parent=None):
        super().__init__(parent)
        self._username     = username
        self._engine       = engine
        self._active       = False
        self._session_mode = "smart"
        self._popup_open   = False
        self._on_break     = False
        self._break_time_left = 0
        self._total_break_secs = 0

        # Break suggestion state — only one suggestion per session
        self._break_suggested  = False
        self._auto_break_timer = QTimer()
        self._auto_break_timer.setSingleShot(True)
        self._auto_break_timer.timeout.connect(self._maybe_suggest_break)

        self._break_timer_state = "running"
        self._break_timer_type  = "stopwatch"
        self._break_actual_elapsed_secs = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16); root.setSpacing(12)

        # ─ Top nav ──────────────────────────────
        nav = QHBoxLayout(); nav.setSpacing(8)

        self.btn_back_main = _back_btn("← Menu")
        self.btn_back_main.clicked.connect(self._go_back_to_select)
        nav.addWidget(self.btn_back_main)

        self._plan_lbl = _label(
            f"Target: {engine.study_mins}m Study / {engine.break_mins}m Break","label_muted")
        nav.addWidget(self._plan_lbl); nav.addStretch()

        for txt, sig in [("Stats", self.sig_show_stats),
                         ("Profile", self.sig_show_profile),
                         ("⚙", self.sig_show_settings)]:
            b = _btn(txt, "btn_secondary")
            b.setFixedHeight(32)
            if txt == "⚙":
                b.setFixedWidth(36)
                b.setStyleSheet(
                    f"font-size:18px; background:{PALETTE['bg_panel']};"
                    f"border:1px solid {PALETTE['border']}; border-radius:8px; color:{PALETTE['text_hi']};")
            else:
                b.setMinimumWidth(80)
            b.clicked.connect(sig.emit)
            nav.addWidget(b)
        root.addLayout(nav)

        # ─ Camera feed ──────────────────────────
        self._vid = QLabel()
        self._vid.setFixedSize(640,360)
        self._vid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vid.setStyleSheet(f"border:2px solid {PALETTE['border']}; background:#000; border-radius:8px;")
        root.addWidget(self._vid, alignment=Qt.AlignmentFlag.AlignCenter)

        # ─ Break overlay panel ──────────────────
        self._break_widget = QFrame(); self._break_widget.setObjectName("card")
        self._break_widget.setFixedSize(640,360)
        self._break_widget.setStyleSheet(
            f"QFrame#card {{ background-color:{PALETTE['bg_panel']}; border:2px solid {PALETTE['border']}; border-radius:12px; }}"
        )
        blay = QVBoxLayout(self._break_widget)
        blay.setContentsMargins(32,28,32,28); blay.setSpacing(10)
        blay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._break_title_lbl = _label("Break Time","label_heading",bold=True,size=22)
        self._break_title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._break_timer_lbl = QLabel("05:00")
        self._break_timer_lbl.setFont(QFont("Consolas",48,QFont.Weight.Bold))
        self._break_timer_lbl.setStyleSheet(f"color:{PALETTE['accent']};")
        self._break_timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._break_quote_lbl = _label("","label_subheading")
        self._break_quote_lbl.setWordWrap(True)
        self._break_quote_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._break_quote_lbl.setStyleSheet("color:#b3b3b3; font-style:italic; font-size:14px;")

        # Deep-work break controls
        self._break_ctrl_widget = QWidget()
        bc_layout = QHBoxLayout(self._break_ctrl_widget)
        bc_layout.setContentsMargins(0,4,0,4); bc_layout.setSpacing(12)
        bc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_dur = QLabel("Break length:")
        lbl_dur.setStyleSheet(f"color:{PALETTE['text_med']}; font-size:13px;")
        lbl_dur.setFixedWidth(90)

        self._break_duration_selector = QComboBox()
        self._break_duration_selector.addItems(["5 Minutes","10 Minutes","15 Minutes","Custom","Unlimited"])
        self._break_duration_selector.setFixedWidth(150)
        self._break_duration_selector.setFixedHeight(36)
        self._break_duration_selector.currentIndexChanged.connect(self._on_break_duration_changed)

        lbl_custom = QLabel("min:")
        lbl_custom.setStyleSheet(f"color:{PALETTE['text_med']}; font-size:13px;")
        lbl_custom.setFixedWidth(28)

        _spin_style = (
            f"QSpinBox {{ background:{PALETTE['bg_input']}; border:1px solid {PALETTE['border']};"
            f"border-radius:8px; padding:6px 10px; color:{PALETTE['text_hi']}; font-size:15px; }}"
            f"QSpinBox:focus {{ border:1px solid {PALETTE['accent']}; }}"
        )
        self._break_custom_spin = QSpinBox()
        self._break_custom_spin.setRange(1, 180); self._break_custom_spin.setValue(10)
        self._break_custom_spin.setMinimumWidth(100); self._break_custom_spin.setFixedHeight(36)
        self._break_custom_spin.setStyleSheet(_spin_style)
        self._break_custom_spin.hide()
        self._lbl_custom_min = lbl_custom
        self._lbl_custom_min.hide()
        self._break_custom_spin.valueChanged.connect(self._on_custom_break_spin_changed)

        bc_layout.addWidget(lbl_dur)
        bc_layout.addWidget(self._break_duration_selector)
        bc_layout.addWidget(self._lbl_custom_min)
        bc_layout.addWidget(self._break_custom_spin)

        btn_resume = _btn("RESUME STUDYING"); btn_resume.setFixedWidth(200)
        btn_resume.clicked.connect(self._end_break)

        btn_end = _btn("END SESSION", "btn_danger"); btn_end.setFixedWidth(200)
        btn_end.clicked.connect(self._go_back_to_select)

        blay.addWidget(self._break_title_lbl)
        blay.addWidget(self._break_timer_lbl)
        blay.addWidget(self._break_quote_lbl)
        blay.addWidget(self._break_ctrl_widget)
        blay.addWidget(HDivider())
        blay.addWidget(btn_resume, alignment=Qt.AlignmentFlag.AlignCenter)
        blay.addWidget(btn_end, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addWidget(self._break_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self._break_widget.hide()

        # ─ Calibrate row ─────────────────────────
        self._calibrate_row = QWidget()
        cal_layout = QHBoxLayout(self._calibrate_row)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        cal_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cal_layout.setSpacing(10)

        btn_calibrate = _btn("⊕ Calibrate Gaze", "btn_secondary")
        btn_calibrate.setFixedHeight(28)
        btn_calibrate.setToolTip(
            "Set your current head position as the neutral reference point.\n"
            "Use this if gaze detection feels off or you've shifted in your seat."
        )
        btn_calibrate.setStyleSheet(
            f"font-size:12px; font-weight:600; background:{PALETTE['bg_panel']};"
            f"border:1px solid {PALETTE['border']}; border-radius:7px;"
            f"color:{PALETTE['text_med']}; padding: 0 12px;"
        )
        btn_calibrate.clicked.connect(self._calibrate)

        self._calibrate_lbl = QLabel("")
        self._calibrate_lbl.setStyleSheet(
            f"color:{PALETTE['accent']}; font-size:12px;"
        )
        self._calibrate_lbl.hide()

        cal_layout.addWidget(btn_calibrate)
        cal_layout.addWidget(self._calibrate_lbl)
        root.addWidget(self._calibrate_row, alignment=Qt.AlignmentFlag.AlignCenter)
        self._calibrate_row.hide()

        # ─ Status + timer ────────────────────────
        self._status_lbl = QLabel("READY")
        self._status_lbl.setFont(QFont("Segoe UI",17,QFont.Weight.Bold))
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._timer_lbl = QLabel("25:00")
        self._timer_lbl.setFont(QFont("Consolas",58,QFont.Weight.Bold))
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer_lbl.setStyleSheet(f"color:{PALETTE['accent']};")

        root.addWidget(self._status_lbl); root.addWidget(self._timer_lbl)

        # ─ Standard (smart/custom) control button ─
        self._btn = _btn("Start Studying"); self._btn.setFixedWidth(220)
        self._btn.clicked.connect(self._toggle)
        root.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._btn_end_session = _btn("END SESSION", "btn_danger")
        self._btn_end_session.setFixedWidth(220)
        self._btn_end_session.clicked.connect(self._go_back_to_select)
        self._btn_end_session.hide()
        root.addWidget(self._btn_end_session, alignment=Qt.AlignmentFlag.AlignCenter)

        # ─ Deep-work control buttons ─────────────
        self._deep_widget = QWidget()
        dl = QHBoxLayout(self._deep_widget)
        dl.setContentsMargins(0,0,0,0); dl.setSpacing(14)
        dl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_deep_pause = _btn("Start Studying"); self.btn_deep_pause.setFixedWidth(160)
        self.btn_deep_pause.clicked.connect(self._deep_toggle)
        self.btn_deep_break = _btn("TAKE BREAK","btn_secondary"); self.btn_deep_break.setFixedWidth(160)
        self.btn_deep_break.clicked.connect(self._start_break); self.btn_deep_break.setEnabled(False)
        self.btn_deep_end   = _btn("END SESSION","btn_danger"); self.btn_deep_end.setFixedWidth(160)
        self.btn_deep_end.clicked.connect(self._deep_end); self.btn_deep_end.setEnabled(False)

        dl.addWidget(self.btn_deep_pause); dl.addWidget(self.btn_deep_break); dl.addWidget(self.btn_deep_end)
        root.addWidget(self._deep_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self._deep_widget.hide()

        self._time_left = engine.study_mins * 60
        self._qt_timer  = QTimer(); self._qt_timer.timeout.connect(self._tick)

    # ── public ───────────────────────────────────

    def update_frame(self, frame: np.ndarray) -> None:
        if self._on_break:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, rgb.shape[1], rgb.shape[0],
                     rgb.shape[1]*3, QImage.Format.Format_RGB888)
        self._vid.setPixmap(QPixmap.fromImage(img).scaled(
            640, 360, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self._refresh_status()

        if getattr(self._engine, "fatigue_pause_requested", False) and self._active:
            self._engine.fatigue_pause_requested = False
            self._start_break()
            return

        # FIX: use recent_transition_count() to decide if a break should be
        # suggested.  The old code checked engine.should_pause_timer which is
        # never set to True in the current biometric engine — so break
        # suggestions in smart/custom mode never fired.
        if (not self._active
                or self._popup_open
                or self._break_suggested
                or self._on_break
                or self._session_mode == "deep"):
            return

        elapsed_secs = (self._engine.study_mins * 60) - self._time_left
        if (elapsed_secs >= 300
                and self._engine.recent_transition_count(_BREAK_CHECK_WINDOW)
                    >= _BREAK_TRANSITIONS):
            self._trigger_break_dialog()

    def refresh_plan(self, reset_timer: bool = False) -> None:
        if self._session_mode == "deep":
            self._plan_lbl.setText("Deep Work Mode — No interruptions")
            if reset_timer: self._time_left = 0
            self._sync_timer_label()
        else:
            self._plan_lbl.setText(
                f"Target: {self._engine.study_mins}m Study / {self._engine.break_mins}m Break")
            if reset_timer: self._time_left = self._engine.study_mins * 60
            self._sync_timer_label()

    def set_session_mode(self, mode: str, study_mins: int = 25, break_mins: int = 10) -> None:
        self._session_mode    = mode
        self._popup_open      = False
        self._on_break        = False
        self._total_break_secs= 0
        self._break_suggested = False
        self._auto_break_timer.stop()

        self._break_widget.hide(); self._vid.show()
        self._status_lbl.show(); self._timer_lbl.show()

        if mode == "deep":
            self._engine.study_mins = 0
            self._engine.break_mins = break_mins
            self._time_left         = 0
            self._plan_lbl.setText("Deep Work Mode — No interruptions")
            self._timer_lbl.setText("00:00")
            self._btn.hide(); self._deep_widget.show()
            self.btn_deep_pause.setText("Start Studying")
            self.btn_deep_pause.setObjectName("")
            self.btn_deep_pause.setStyle(self.btn_deep_pause.style())
            self.btn_deep_break.setEnabled(False); self.btn_deep_end.setEnabled(False)
        else:
            self._engine.study_mins = study_mins
            self._engine.break_mins = max(5, break_mins)   # ensure break ≥ 5 min
            self.refresh_plan(reset_timer=True)
            self._btn.show(); self._deep_widget.hide()
            self._btn.setText("Start Studying")
            self._btn.setObjectName(""); self._btn.setStyle(self._btn.style())

    @property
    def is_active(self) -> bool:
        return self._active

    # ── private helpers ───────────────────────────

    def _schedule_auto_break(self) -> None:
        """
        Schedule one automatic break-suggestion at ~55 % of session time.
        Minimum trigger: 5 minutes (300 s).  Maximum: 80 % of total time.
        This acts as a backstop in case the biometric transition count never
        reaches the threshold (e.g. the user stays perfectly focused).
        """
        if self._session_mode == "deep" or self._break_suggested:
            return
        total_secs = self._engine.study_mins * 60
        target_pct = 0.55
        trigger_at = max(300, min(int(total_secs * target_pct),
                                  int(total_secs * 0.80)))
        self._auto_break_timer.start(trigger_at * 1000)

    def _maybe_suggest_break(self) -> None:
        """Called by the auto-break timer when it fires."""
        if not self._active or self._on_break or self._break_suggested or self._popup_open:
            return
        elapsed = (self._engine.study_mins * 60) - self._time_left
        if elapsed >= 300:
            self._trigger_break_dialog()

    def _trigger_break_dialog(self) -> None:
        """Show the Take-a-Break dialog (once per session)."""
        if self._break_suggested or self._popup_open:
            return
        self._break_suggested = True
        self._popup_open      = True
        self._auto_break_timer.stop()
        self._qt_timer.stop()

        dlg = BreakDialog(self._engine.focus_score(), self.window())
        res = dlg.exec()
        self._popup_open = False

        if res == QDialog.DialogCode.Accepted:
            self._start_break()
        else:
            # User skipped — reset engine records and resume
            self._engine.reset_records()
            if self._active:
                self._qt_timer.start(1000)

    def _go_back_to_select(self):
        self._active = False
        self._qt_timer.stop(); self._auto_break_timer.stop()
        self._on_break = False
        self._calibrate_row.hide()
        self.sig_session_ended.emit()

    def _calibrate(self) -> None:
        """Set the user's current head position as the neutral gaze reference."""
        self._engine.calibrate_center()
        self._calibrate_lbl.setText("✓ Calibrated")
        self._calibrate_lbl.show()
        QTimer.singleShot(2500, self._calibrate_lbl.hide)

    def _start_break(self):
        self._on_break = True
        self._qt_timer.stop(); self._auto_break_timer.stop()
        self.sig_session_paused.emit()
        self._calibrate_row.hide()

        self._break_quote_lbl.setText(random.choice(BREAK_QUOTES))
        self._break_actual_elapsed_secs = 0
        self._break_title_lbl.setText("Break Time")

        if self._session_mode == "deep":
            self._break_ctrl_widget.show()
            self._break_duration_selector.blockSignals(True)
            self._break_duration_selector.setCurrentIndex(0)   # "5 Minutes"
            self._break_duration_selector.blockSignals(False)
            self._break_time_left  = 5 * 60
            self._break_timer_state = "running"
            self._break_timer_type  = "countdown"
            self._break_custom_spin.hide(); self._lbl_custom_min.hide()
        else:
            # Break duration = half the configured break_mins, minimum 5 min
            half_break = max(5, self._engine.break_mins // 2)
            self._break_time_left = half_break * 60
            self._break_ctrl_widget.hide()

        self._sync_break_timer_label()

        self._vid.hide(); self._status_lbl.hide(); self._timer_lbl.hide()
        self._btn.hide(); self._deep_widget.hide()
        self._break_widget.show()
        self._active = False
        self._qt_timer.start(1000)

    def _end_break(self):
        self._on_break = False; self._qt_timer.stop()
        self._break_widget.hide()
        self._vid.show(); self._status_lbl.show(); self._timer_lbl.show()
        self._calibrate_row.show()

        if self._session_mode == "deep":
            self._total_break_secs += self._break_actual_elapsed_secs
            self._deep_widget.show()
            self.btn_deep_pause.setText("PAUSE SESSION")
            self.btn_deep_pause.setObjectName("btn_secondary")
            self.btn_deep_pause.setStyle(self.btn_deep_pause.style())
            self.btn_deep_break.setEnabled(True); self.btn_deep_end.setEnabled(True)
        else:
            self._btn.show()
            self._btn.setText("PAUSE SESSION")
            self._btn_end_session.show()
            self._btn.setObjectName("btn_secondary")
            self._btn.setStyle(self._btn.style())

        self._engine.reset_records()
        if hasattr(self._engine, "fatigue_triggered"):
            self._engine.fatigue_triggered = False

        self._active = True
        self._qt_timer.start(1000); self.sig_session_started.emit()

    def _sync_break_timer_label(self):
        m,s = divmod(self._break_time_left,60)
        self._break_timer_lbl.setText(f"{m:02d}:{s:02d}")

    def _on_break_duration_changed(self, index: int) -> None:
        self._break_timer_state = "running"
        items = ["5 Minutes","10 Minutes","15 Minutes","Custom","Unlimited"]
        sel   = items[index] if index < len(items) else "5 Minutes"
        if sel == "Custom":
            self._break_timer_type = "countdown"
            self._break_custom_spin.show(); self._lbl_custom_min.show()
            self._break_time_left = self._break_custom_spin.value() * 60
        elif sel == "Unlimited":
            self._break_timer_type = "stopwatch"
            self._break_custom_spin.hide(); self._lbl_custom_min.hide()
            self._break_time_left = 0
        else:
            self._break_timer_type = "countdown"
            self._break_custom_spin.hide(); self._lbl_custom_min.hide()
            mins_map = {"5 Minutes":5,"10 Minutes":10,"15 Minutes":15}
            self._break_time_left = mins_map.get(sel,5) * 60
        self._sync_break_timer_label()

    def _on_custom_break_spin_changed(self, val: int) -> None:
        items = ["5 Minutes","10 Minutes","15 Minutes","Custom","Unlimited"]
        if self._break_duration_selector.currentIndex() < len(items) and \
           items[self._break_duration_selector.currentIndex()] == "Custom":
            self._break_time_left = val * 60
            self._sync_break_timer_label()
            self._break_timer_state = "running"

    def _play_alert_sound(self) -> None:
        try:
            import winsound
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            try: QApplication.beep()
            except Exception: pass

    def _toggle(self):
        self._active = not self._active
        if self._active:
            self._qt_timer.start(1000)
            self._btn.setText("PAUSE SESSION")
            self._btn_end_session.hide(); self._btn.setObjectName("btn_danger")
            self._calibrate_row.show()
            self._schedule_auto_break()
            self.sig_session_started.emit()
        else:
            self._qt_timer.stop(); self._auto_break_timer.stop()
            self._btn.setText("RESUME SESSION")
            self._btn_end_session.show(); self._btn.setObjectName("btn_secondary")
            self._calibrate_row.hide()
            self.sig_session_paused.emit()
        self._btn.setStyle(self._btn.style())

    def _deep_toggle(self):
        self._active = not self._active
        if self._active:
            self._qt_timer.start(1000)
            self.btn_deep_pause.setText("PAUSE SESSION")
            self.btn_deep_pause.setObjectName("btn_secondary")
            self.btn_deep_break.setEnabled(True); self.btn_deep_end.setEnabled(True)
            self._calibrate_row.show()
            self.sig_session_started.emit()
        else:
            self._qt_timer.stop()
            self.btn_deep_pause.setText("RESUME SESSION")
            self.btn_deep_pause.setObjectName("")
            self.btn_deep_break.setEnabled(False)
            self._calibrate_row.hide()
            self.sig_session_paused.emit()
        self.btn_deep_pause.setStyle(self.btn_deep_pause.style())

    def _deep_end(self):
        self._active = False; self._qt_timer.stop(); self._session_complete()

    def _tick(self):
        if self._on_break:
            if self._session_mode == "deep":
                if self._break_timer_state == "completed":
                    return
                self._break_actual_elapsed_secs += 1
                if self._break_timer_type == "stopwatch":
                    self._break_time_left += 1; self._sync_break_timer_label()
                else:
                    if self._break_time_left > 0:
                        self._break_time_left -= 1; self._sync_break_timer_label()
                        if self._break_time_left == 0:
                            self._break_timer_state = "completed"; self._play_alert_sound()
            else:
                if self._break_time_left > 0:
                    self._break_time_left -= 1; self._sync_break_timer_label()
                else:
                    self._end_break()
            return

        if self._session_mode == "deep":
            self._time_left += 1; self._sync_timer_label()
        else:
            if self._time_left > 0:
                self._time_left -= 1; self._sync_timer_label()
            else:
                self._session_complete()

    def _session_complete(self):
        self._active = False; self._qt_timer.stop(); self._auto_break_timer.stop()
        score = self._engine.update_ml_plan()
        if self._session_mode == "deep":
            # In deep mode _time_left is a stopwatch counting up from 0,
            # so its value at completion is the total elapsed seconds.
            elapsed_mins = max(1, self._time_left // 60)
            break_mins   = self._total_break_secs // 60
            storage.save_session(self._username, score, elapsed_mins, break_mins)
        else:
            storage.save_session(self._username, score,
                                 self._engine.study_mins, self._engine.break_mins)
        self.refresh_plan(reset_timer=True)
        self._btn.setText("START NEXT BLOCK" if self._session_mode != "deep" else "Start Studying")
        self._btn.setObjectName(""); self._btn.setStyle(self._btn.style())
        self.sig_session_ended.emit()

    def _sync_timer_label(self):
        m,s = divmod(self._time_left,60); self._timer_lbl.setText(f"{m:02d}:{s:02d}")

    def _refresh_status(self):
        st = self._engine.status
        _SC = {
            "Focused":          PALETTE["accent"],
            "Paused":           PALETTE["text_med"],
            "Ready":            PALETTE["text_med"],
            "POOR POSTURE":     PALETTE["warning"],
            "NOT FOCUSED":      PALETTE["danger"],
            "WARNING: DROWSY":  PALETTE["danger"],
            "FATIGUED":         PALETTE["danger"],
            "FACE NOT FOUND":   PALETTE["text_med"],
            "TAKE A BREAK":     PALETTE["warning"],
        }
        color = _SC.get(st, PALETTE["danger"])
        self._status_lbl.setText(st)
        self._status_lbl.setStyleSheet(f"color:{color}; font-weight:700;")


# ──────────────────────────────────────────────
# SESSION SELECT PAGE
# ──────────────────────────────────────────────

class ClickableCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(160); self.setFixedWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24,20,24,20); layout.setSpacing(12)
        title_lbl = _label(title, bold=True, size=17)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl  = _label(description, "label_muted"); desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl); layout.addWidget(desc_lbl); layout.addStretch()

    def mousePressEvent(self, event):
        self.clicked.emit(); super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet(
                f"QFrame#card {{ background-color:{PALETTE['bg_panel']}; border:2px solid {PALETTE['accent']}; border-radius:12px; }}")
        else:
            self.setStyleSheet("")


class SessionSelectPage(QWidget):
    sig_start_session = pyqtSignal(str, int, int)
    sig_show_stats    = pyqtSignal()
    sig_show_profile  = pyqtSignal()
    sig_show_settings = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40,30,40,30); outer.setSpacing(20)

        top_nav = QHBoxLayout(); top_nav.setSpacing(8); top_nav.addStretch()
        for txt, sig in [("Stats", self.sig_show_stats),
                         ("Profile", self.sig_show_profile),
                         ("⚙", self.sig_show_settings)]:
            b = _btn(txt, "btn_secondary"); b.setFixedHeight(32)
            if txt == "⚙":
                b.setFixedWidth(36)
                b.setStyleSheet(
                    f"font-size:18px; background:{PALETTE['bg_panel']};"
                    f"border:1px solid {PALETTE['border']}; border-radius:8px; color:{PALETTE['text_hi']};")
            else:
                b.setMinimumWidth(80)
            b.clicked.connect(sig.emit); top_nav.addWidget(b)
        outer.addLayout(top_nav)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = _label("Choose Your Study Style","label_heading",bold=True,size=25)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = _label("Select a flow to start studying.","label_subheading")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title); outer.addWidget(subtitle); outer.addWidget(HDivider())

        cards_row = QHBoxLayout(); cards_row.setSpacing(20)
        cards_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_deep   = ClickableCard("Deep Work",    "No interruptions. You decide when to stop.")
        self.card_smart  = ClickableCard("Smart Session","AI monitors focus and suggests breaks.")
        self.card_custom = ClickableCard("Custom",       "You set the time, you set the pace.")
        cards_row.addWidget(self.card_deep)
        cards_row.addWidget(self.card_smart)
        cards_row.addWidget(self.card_custom)
        outer.addLayout(cards_row)

        # Custom duration widget
        cw_outer = QHBoxLayout()
        cw_outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.custom_widget = QFrame()
        self.custom_widget.setObjectName("card")
        self.custom_widget.setFixedWidth(360)
        cw_layout = QVBoxLayout(self.custom_widget)
        cw_layout.setContentsMargins(24, 16, 24, 16); cw_layout.setSpacing(12)

        cw_layout.addWidget(_label("Session Timing", "label_muted"))
        cw_layout.addWidget(HDivider())

        _spin_style = (
            f"QSpinBox {{ background:{PALETTE['bg_input']}; border:1px solid {PALETTE['border']};"
            f"border-radius:8px; padding:6px 8px; color:{PALETTE['text_hi']}; font-size:15px; }}"
            f"QSpinBox:focus {{ border:1px solid {PALETTE['accent']}; }}"
        )

        row_study = QHBoxLayout(); row_study.setSpacing(16)
        lbl_study = QLabel("Study (min):")
        lbl_study.setFixedWidth(120)
        lbl_study.setStyleSheet(f"color:{PALETTE['text_hi']}; font-size:14px;")
        self.spin_study = QSpinBox()
        self.spin_study.setRange(1, 180); self.spin_study.setValue(25)
        self.spin_study.setMinimumWidth(100); self.spin_study.setFixedHeight(38)
        self.spin_study.setStyleSheet(_spin_style)
        row_study.addWidget(lbl_study); row_study.addWidget(self.spin_study)

        row_break = QHBoxLayout(); row_break.setSpacing(16)
        lbl_break = QLabel("Break (min):")
        lbl_break.setFixedWidth(120)
        lbl_break.setStyleSheet(f"color:{PALETTE['text_hi']}; font-size:14px;")
        self.spin_break = QSpinBox()
        self.spin_break.setRange(1, 60); self.spin_break.setValue(5)
        self.spin_break.setMinimumWidth(100); self.spin_break.setFixedHeight(38)
        self.spin_break.setStyleSheet(_spin_style)
        row_break.addWidget(lbl_break); row_break.addWidget(self.spin_break)

        cw_layout.addLayout(row_study); cw_layout.addLayout(row_break)

        cw_outer.addWidget(self.custom_widget)
        outer.addLayout(cw_outer)
        self.custom_widget.hide()

        self.btn_start = _btn("Start Studying"); self.btn_start.setFixedWidth(220)
        self.btn_start.setEnabled(False); self.btn_start.clicked.connect(self._on_start)
        outer.addWidget(self.btn_start, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addStretch()

        self.card_deep.clicked.connect(lambda: self._select_mode("deep"))
        self.card_smart.clicked.connect(lambda: self._select_mode("smart"))
        self.card_custom.clicked.connect(lambda: self._select_mode("custom"))
        self._selected_mode = None

    def _select_mode(self, mode: str):
        self._selected_mode = mode
        self.card_deep.set_selected(mode=="deep")
        self.card_smart.set_selected(mode=="smart")
        self.card_custom.set_selected(mode=="custom")
        self.custom_widget.setVisible(mode=="custom")
        self.btn_start.setEnabled(True)

    def _on_start(self):
        if self._selected_mode == "custom":
            study_mins = self.spin_study.value()
            break_mins = self.spin_break.value()
        elif self._selected_mode == "smart":
            # Smart mode uses engine-managed defaults; pass sensible values
            study_mins = 25
            break_mins = 10
        else:
            # Deep work — study_mins unused, break_mins used for break panel default
            study_mins = 0
            break_mins = 10
        self.sig_start_session.emit(self._selected_mode, study_mins, break_mins)


# ──────────────────────────────────────────────
# BREAK DIALOG
# ──────────────────────────────────────────────

class BreakDialog(QDialog):
    def __init__(self, focus_score: float, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True); self.setFixedWidth(440)
        self.setStyleSheet(
            f"QDialog {{ background-color:{PALETTE['bg_deep']}; border:1.5px solid {PALETTE['border']}; border-radius:12px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32,28,32,28); layout.setSpacing(14)

        title_lbl = _label("Time for a Break?","label_heading",bold=True,size=24)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_lbl = _label(
            "You've been working hard! A short break helps you stay sharp for the rest of the session.",
            "label_subheading")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); sub_lbl.setWordWrap(True)

        stat_card = StatCard("Focus Score", f"{focus_score:.1f}", "%")

        tip_lbl = QLabel(random.choice([
            "Looking away from your screen for 20 seconds reduces eye strain.",
            "A 5-minute stretch can boost focus by up to 20%.",
            "Staying hydrated improves concentration and memory.",
            "A short walk, even inside, resets your attention span.",
        ]))
        tip_lbl.setWordWrap(True)
        tip_lbl.setStyleSheet(
            f"color:{PALETTE['text_med']}; font-size:13px; font-style:italic;"
            f"border-left:3px solid {PALETTE['accent']}; padding-left:10px;")

        btn_row = QHBoxLayout(); btn_row.setSpacing(14)
        btn_take = _btn("Take Break")
        btn_skip = _btn("Skip", "btn_secondary")
        btn_take.clicked.connect(self.accept); btn_skip.clicked.connect(self.reject)
        btn_row.addWidget(btn_take); btn_row.addWidget(btn_skip)

        layout.addWidget(title_lbl); layout.addWidget(sub_lbl)
        layout.addWidget(stat_card); layout.addWidget(tip_lbl)
        layout.addWidget(HDivider()); layout.addLayout(btn_row)