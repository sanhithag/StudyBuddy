"""
pages.py — StudyBuddy AI
All QWidget page classes:
  LoginPage, RegisterPage, ForgotPasswordPage,
  ProfilePage, StatsPage, SettingsPage, WorkspacePage
"""

import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QFrame,
    QScrollArea, QDoubleSpinBox, QComboBox, QGridLayout,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage

import cv2
import numpy as np

import storage
from theme import PALETTE, AVATAR_COLORS
from widgets import HDivider, StatCard, AvatarCircle, ColorPickerRow, MessageBanner


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _label(text, obj_name="", bold=False, size=13):
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


def _section_card(content_widget: QWidget) -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    layout.addWidget(content_widget)
    return card


# ──────────────────────────────────────────────
# LOGIN PAGE
# ──────────────────────────────────────────────

class LoginPage(QWidget):
    sig_logged_in = pyqtSignal(str)      # emits username
    sig_go_register = pyqtSignal()
    sig_go_forgot = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame()
        box.setObjectName("card")
        box.setFixedWidth(400)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(14)

        # Logo / heading
        logo = _label("StudyBuddy AI", "label_heading", bold=True, size=26)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = _label("Focus. Learn. Adapt.", "label_subheading")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.user = _field("Username")
        self.pwd  = _field("Password", password=True)
        self.banner = MessageBanner()

        btn_login = _btn("LOG IN")
        btn_login.clicked.connect(self._login)

        row = QHBoxLayout()
        btn_reg = _btn("Create account", "btn_ghost")
        btn_forgot = _btn("Forgot password?", "btn_ghost")
        btn_reg.clicked.connect(self.sig_go_register.emit)
        btn_forgot.clicked.connect(self.sig_go_forgot.emit)
        row.addWidget(btn_reg)
        row.addStretch()
        row.addWidget(btn_forgot)

        for w in [logo, sub, HDivider(), self.user, self.pwd,
                  self.banner, btn_login]:
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
            self.sig_logged_in.emit(u)
        else:
            self.banner.show_error(msg)


# ──────────────────────────────────────────────
# REGISTER PAGE
# ──────────────────────────────────────────────

class RegisterPage(QWidget):
    sig_registered = pyqtSignal(str)
    sig_go_login = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame()
        box.setObjectName("card")
        box.setFixedWidth(440)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(12)

        layout.addWidget(_label("Create Account", "label_heading", bold=True))
        layout.addWidget(HDivider())

        self.full_name = _field("Full name")
        self.email     = _field("Email (optional)")
        self.user      = _field("Username")
        self.pwd       = _field("Password", password=True)
        self.pwd2      = _field("Confirm password", password=True)

        layout.addWidget(_label("Security question (for password recovery)"))
        self.q_combo = QComboBox()
        self.q_combo.addItems(storage.SECURITY_QUESTIONS)
        self.sec_ans = _field("Your answer")

        self.banner = MessageBanner()
        btn_reg = _btn("CREATE ACCOUNT")
        btn_reg.clicked.connect(self._register)
        btn_back = _btn("← Back to login", "btn_ghost")
        btn_back.clicked.connect(self.sig_go_login.emit)

        for w in [self.full_name, self.email, HDivider(),
                  self.user, self.pwd, self.pwd2, HDivider(),
                  self.q_combo, self.sec_ans, self.banner,
                  btn_reg, btn_back]:
            layout.addWidget(w)

        outer.addWidget(box, alignment=Qt.AlignmentFlag.AlignCenter)

    def _register(self):
        fn   = self.full_name.text().strip()
        em   = self.email.text().strip()
        u    = self.user.text().strip()
        p    = self.pwd.text()
        p2   = self.pwd2.text()
        q    = self.q_combo.currentText()
        ans  = self.sec_ans.text().strip()

        if not u or not p:
            self.banner.show_error("Username and password are required.")
            return
        if p != p2:
            self.banner.show_error("Passwords do not match.")
            return
        if len(p) < 6:
            self.banner.show_error("Password must be at least 6 characters.")
            return
        if not ans:
            self.banner.show_error("Please provide a security answer.")
            return

        ok, msg = storage.register_user(u, p, fn, em)
        if not ok:
            self.banner.show_error(msg)
            return
        storage.set_security_question(u, q, ans)
        self.banner.show_success("Account created! Logging you in…")
        QTimer.singleShot(800, lambda: self.sig_registered.emit(u))


# ──────────────────────────────────────────────
# FORGOT PASSWORD PAGE
# ──────────────────────────────────────────────

class ForgotPasswordPage(QWidget):
    sig_go_login = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame()
        box.setObjectName("card")
        box.setFixedWidth(420)
        self._layout = QVBoxLayout(box)
        self._layout.setContentsMargins(36, 36, 36, 36)
        self._layout.setSpacing(12)

        # Step 1 – enter username
        self._step1 = QWidget()
        l1 = QVBoxLayout(self._step1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.setSpacing(12)
        l1.addWidget(_label("Forgot Password", "label_heading", bold=True))
        l1.addWidget(_label("Enter your username to find your account.", "label_subheading"))
        l1.addWidget(HDivider())
        self.user_input = _field("Username")
        self.banner1 = MessageBanner()
        btn_next = _btn("FIND ACCOUNT")
        btn_next.clicked.connect(self._find_account)
        btn_back = _btn("← Back to login", "btn_ghost")
        btn_back.clicked.connect(self.sig_go_login.emit)
        for w in [self.user_input, self.banner1, btn_next, btn_back]:
            l1.addWidget(w)

        # Step 2 – answer security question + set new password
        self._step2 = QWidget()
        l2 = QVBoxLayout(self._step2)
        l2.setContentsMargins(0, 0, 0, 0)
        l2.setSpacing(12)
        self.q_label  = _label("", "label_subheading")
        self.q_label.setWordWrap(True)
        self.ans_input = _field("Your answer")
        self.new_pwd   = _field("New password", password=True)
        self.new_pwd2  = _field("Confirm new password", password=True)
        self.banner2   = MessageBanner()
        btn_reset = _btn("RESET PASSWORD")
        btn_reset.clicked.connect(self._reset)
        for w in [_label("Answer your security question", "label_heading", bold=True),
                  HDivider(), self.q_label,
                  self.ans_input, self.new_pwd, self.new_pwd2,
                  self.banner2, btn_reset]:
            l2.addWidget(w)

        self._layout.addWidget(self._step1)
        self._layout.addWidget(self._step2)
        self._step2.hide()

        outer.addWidget(box, alignment=Qt.AlignmentFlag.AlignCenter)

    def _find_account(self):
        u = self.user_input.text().strip()
        q = storage.get_security_question(u)
        if not q:
            self.banner1.show_error("Username not found or no security question set.")
            return
        self._username = u
        self.q_label.setText(f"❓  {q}")
        self._step1.hide()
        self._step2.show()

    def _reset(self):
        ans  = self.ans_input.text().strip()
        np_  = self.new_pwd.text()
        np2  = self.new_pwd2.text()
        if np_ != np2:
            self.banner2.show_error("Passwords do not match.")
            return
        if len(np_) < 6:
            self.banner2.show_error("Password must be at least 6 characters.")
            return
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
    sig_back = pyqtSignal()
    sig_logout = pyqtSignal()

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self._username = username
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(40, 30, 40, 30)
        main.setSpacing(20)

        # ─ Header ────────────────────────────
        hdr = QHBoxLayout()
        btn_back = _btn("← Dashboard", "btn_secondary", fixed_w=130)
        btn_back.clicked.connect(self.sig_back.emit)
        hdr.addWidget(btn_back)
        hdr.addStretch()
        btn_logout = _btn("LOG OUT", "btn_danger", fixed_w=100)
        btn_logout.clicked.connect(self.sig_logout.emit)
        hdr.addWidget(btn_logout)
        main.addLayout(hdr)

        # ─ Avatar + name card ─────────────────
        prof = storage.get_profile(username) or {}
        initials = (prof.get("full_name") or username)[:2].upper()
        color    = prof.get("avatar_color", AVATAR_COLORS[0])

        top_card = QFrame()
        top_card.setObjectName("card")
        top_row = QHBoxLayout(top_card)
        top_row.setContentsMargins(24, 20, 24, 20)
        top_row.setSpacing(20)

        self._avatar = AvatarCircle(initials, color, 72)
        top_row.addWidget(self._avatar)

        name_col = QVBoxLayout()
        name_col.setSpacing(4)
        self._name_lbl = _label(prof.get("full_name") or username,
                                bold=True, size=18)
        self._name_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._username_lbl = _label(f"@{username}", "label_muted")
        self._since_lbl = _label(
            f"Member since {prof.get('created_at', '—')}", "label_muted")
        name_col.addWidget(self._name_lbl)
        name_col.addWidget(self._username_lbl)
        name_col.addWidget(self._since_lbl)
        top_row.addLayout(name_col)
        top_row.addStretch()
        main.addWidget(top_card)

        # ─ Edit profile form ─────────────────
        form_card = QFrame()
        form_card.setObjectName("card")
        fl = QVBoxLayout(form_card)
        fl.setContentsMargins(24, 20, 24, 20)
        fl.setSpacing(10)
        fl.addWidget(_label("EDIT PROFILE", "label_muted"))
        fl.addWidget(HDivider())

        self.f_name  = _field("Full name")
        self.f_name.setText(prof.get("full_name", ""))
        self.f_email = _field("Email")
        self.f_email.setText(prof.get("email", ""))

        fl.addWidget(_label("Full name"))
        fl.addWidget(self.f_name)
        fl.addWidget(_label("Email"))
        fl.addWidget(self.f_email)

        fl.addWidget(_label("Daily study goal (hours)"))
        self.f_goal = QDoubleSpinBox()
        self.f_goal.setRange(0.5, 12.0)
        self.f_goal.setSingleStep(0.5)
        self.f_goal.setValue(prof.get("study_goal_hrs", 2.0))
        fl.addWidget(self.f_goal)

        fl.addWidget(_label("Avatar colour"))
        self._color_picker = ColorPickerRow(AVATAR_COLORS, color)
        self._color_picker.color_selected.connect(self._preview_color)
        fl.addWidget(self._color_picker)

        self.prof_banner = MessageBanner()
        btn_save = _btn("SAVE CHANGES")
        btn_save.clicked.connect(self._save_profile)
        fl.addWidget(self.prof_banner)
        fl.addWidget(btn_save)
        main.addWidget(form_card)

        # ─ Change password ────────────────────
        pw_card = QFrame()
        pw_card.setObjectName("card")
        pl = QVBoxLayout(pw_card)
        pl.setContentsMargins(24, 20, 24, 20)
        pl.setSpacing(10)
        pl.addWidget(_label("CHANGE PASSWORD", "label_muted"))
        pl.addWidget(HDivider())
        self.pw_old  = _field("Current password", password=True)
        self.pw_new  = _field("New password", password=True)
        self.pw_new2 = _field("Confirm new password", password=True)
        self.pw_banner = MessageBanner()
        btn_pw = _btn("UPDATE PASSWORD")
        btn_pw.clicked.connect(self._change_password)
        for w in [self.pw_old, self.pw_new, self.pw_new2, self.pw_banner, btn_pw]:
            pl.addWidget(w)
        main.addWidget(pw_card)

        main.addStretch()
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _preview_color(self, color: str) -> None:
        fn = self.f_name.text().strip() or self._username
        self._avatar.set_color(color)
        self._avatar.set_initials(fn[:2])

    def _save_profile(self) -> None:
        fn    = self.f_name.text().strip()
        em    = self.f_email.text().strip()
        goal  = self.f_goal.value()
        color = self._color_picker.current_color()
        ok, msg = storage.update_profile(self._username, fn, em, goal, color)
        if ok:
            self.prof_banner.show_success(msg)
            self._name_lbl.setText(fn or self._username)
            self._avatar.set_initials((fn or self._username)[:2])
            self._avatar.set_color(color)
        else:
            self.prof_banner.show_error(msg)

    def _change_password(self) -> None:
        old = self.pw_old.text()
        new = self.pw_new.text()
        c   = self.pw_new2.text()
        if new != c:
            self.pw_banner.show_error("New passwords do not match.")
            return
        if len(new) < 6:
            self.pw_banner.show_error("Password must be ≥ 6 characters.")
            return
        ok, msg = storage.change_password(self._username, old, new)
        if ok:
            self.pw_banner.show_success(msg)
            self.pw_old.clear(); self.pw_new.clear(); self.pw_new2.clear()
        else:
            self.pw_banner.show_error(msg)


# ──────────────────────────────────────────────
# STATS PAGE
# ──────────────────────────────────────────────

class StatsPage(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self._username = username

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(40, 30, 40, 30)
        main.setSpacing(20)

        hdr = QHBoxLayout()
        hdr.addWidget(_label("📊  Insights", "label_heading", bold=True, size=22))
        hdr.addStretch()
        btn_back = _btn("← Dashboard", "btn_secondary", fixed_w=130)
        btn_back.clicked.connect(self.sig_back.emit)
        hdr.addWidget(btn_back)
        main.addLayout(hdr)

        # Stat cards row
        summary = storage.get_stats_summary(username)
        grid = QGridLayout()
        grid.setSpacing(12)
        cards = [
            StatCard("Sessions", str(summary.get("total_sessions") or 0)),
            StatCard("Avg Focus", f"{summary.get('avg_focus') or 0:.1f}", "%"),
            StatCard("Study Time", str(int((summary.get('total_study_mins') or 0) / 60)), "hrs"),
            StatCard("Active Days", str(summary.get("days_active_week") or 0), "/ wk"),
        ]
        for i, c in enumerate(cards):
            grid.addWidget(c, 0, i)
        main.addLayout(grid)

        # AI coach tip
        score = summary.get("avg_focus") or 0
        if score > 90:
            tip = "🔥 Flow state detected! Try advanced topic interleaving for maximum retention."
        elif score > 70:
            tip = "✅ Solid focus. Apply the 2-minute rule to crush distractions before they snowball."
        elif score > 0:
            tip = "💡 Low focus detected. Consider 15-minute micro-burst sessions with active recall breaks."
        else:
            tip = "📚 No sessions yet. Start your first session to get personalised coaching insights."

        tip_frame = QFrame()
        tip_frame.setObjectName("card")
        tl = QVBoxLayout(tip_frame)
        tl.setContentsMargins(20, 14, 20, 14)
        coach = QLabel(f"AI COACH  —  {tip}")
        coach.setWordWrap(True)
        coach.setStyleSheet(
            f"color: {PALETTE['text_hi']}; border-left: 3px solid {PALETTE['accent']}; padding-left: 12px;"
        )
        tl.addWidget(coach)
        main.addWidget(tip_frame)

        # History table
        main.addWidget(_label("RECENT SESSIONS", "label_muted"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Focus %", "Study (min)", "Break (min)", "Notes"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            self.table.styleSheet() +
            f"alternate-background-color: rgba(255,255,255,0.03);"
        )
        self._load_table()
        main.addWidget(self.table)

        main.addStretch()
        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _load_table(self):
        rows = storage.get_recent_sessions(self._username, 10)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [row["date"], f"{row['focus_score']:.1f}",
                    str(row["study_mins"]), str(row["break_mins"]),
                    row.get("notes", "")]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)


# ──────────────────────────────────────────────
# SETTINGS PAGE
# ──────────────────────────────────────────────

class SettingsPage(QWidget):
    sig_back = pyqtSignal()
    sig_logout = pyqtSignal()
    sig_account_deleted = pyqtSignal()

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self._username = username

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(40, 30, 40, 30)
        main.setSpacing(20)

        hdr = QHBoxLayout()
        hdr.addWidget(_label("⚙️  Settings", "label_heading", bold=True, size=22))
        hdr.addStretch()
        btn_back = _btn("← Dashboard", "btn_secondary", fixed_w=130)
        btn_back.clicked.connect(self.sig_back.emit)
        hdr.addWidget(btn_back)
        main.addLayout(hdr)

        # Security question update
        sq_card = QFrame(); sq_card.setObjectName("card")
        sql = QVBoxLayout(sq_card)
        sql.setContentsMargins(24, 20, 24, 20); sql.setSpacing(10)
        sql.addWidget(_label("UPDATE SECURITY QUESTION", "label_muted"))
        sql.addWidget(HDivider())
        self.sq_combo = QComboBox()
        self.sq_combo.addItems(storage.SECURITY_QUESTIONS)
        self.sq_ans = _field("New answer")
        self.sq_banner = MessageBanner()
        btn_sq = _btn("SAVE QUESTION")
        btn_sq.clicked.connect(self._update_sq)
        for w in [self.sq_combo, self.sq_ans, self.sq_banner, btn_sq]:
            sql.addWidget(w)
        main.addWidget(sq_card)

        # Data management
        data_card = QFrame(); data_card.setObjectName("card")
        dl = QVBoxLayout(data_card)
        dl.setContentsMargins(24, 20, 24, 20); dl.setSpacing(10)
        dl.addWidget(_label("DATA MANAGEMENT", "label_muted"))
        dl.addWidget(HDivider())

        self.data_banner = MessageBanner()
        btn_wipe = _btn("WIPE SESSION HISTORY", "btn_secondary")
        btn_wipe.clicked.connect(self._wipe_history)
        btn_del = _btn("DELETE ACCOUNT", "btn_danger")
        btn_del.clicked.connect(self._delete_account)

        dl.addWidget(QLabel(
            "Wipe all session history (account remains), or permanently delete your account."))
        dl.addWidget(self.data_banner)
        dl.addWidget(btn_wipe)
        dl.addWidget(btn_del)
        main.addWidget(data_card)

        main.addStretch()
        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _update_sq(self):
        ans = self.sq_ans.text().strip()
        if not ans:
            self.sq_banner.show_error("Answer cannot be empty.")
            return
        storage.set_security_question(self._username, self.sq_combo.currentText(), ans)
        self.sq_banner.show_success("Security question updated.")

    def _wipe_history(self):
        storage.delete_all_sessions(self._username)
        self.data_banner.show_success("All session history wiped.")

    def _delete_account(self):
        storage.delete_account(self._username)
        self.sig_account_deleted.emit()


# ──────────────────────────────────────────────
# WORKSPACE PAGE  (camera + timer)
# ──────────────────────────────────────────────

class WorkspacePage(QWidget):
    sig_show_stats = pyqtSignal()
    sig_show_profile = pyqtSignal()
    sig_show_settings = pyqtSignal()

    def __init__(self, username: str, engine, parent=None):
        super().__init__(parent)
        self._username = username
        self._engine   = engine
        self._active   = False

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ─ Top nav ───────────────────────────────
        nav = QHBoxLayout()
        self._plan_lbl = _label(
            f"Target: {engine.study_mins}m Study / {engine.break_mins}m Break", "label_muted")
        nav.addWidget(self._plan_lbl)
        nav.addStretch()

        for txt, sig in [("Stats", self.sig_show_stats),
                         ("Profile", self.sig_show_profile),
                         ("⚙️", self.sig_show_settings)]:
            b = _btn(txt, "btn_secondary")
            if txt == "⚙️":
                b.setFixedWidth(40)
            b.clicked.connect(sig.emit)
            nav.addWidget(b)
        root.addLayout(nav)

        # ─ Camera feed ───────────────────────────
        self._vid = QLabel()
        self._vid.setFixedSize(640, 360)
        self._vid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vid.setStyleSheet(
            f"border: 2px solid {PALETTE['border']}; background: #000; border-radius: 8px;")
        root.addWidget(self._vid, alignment=Qt.AlignmentFlag.AlignCenter)

        # ─ Status + timer ─────────────────────────
        self._status_lbl = QLabel("READY")
        self._status_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._timer_lbl = QLabel("25:00")
        self._timer_lbl.setFont(QFont("Consolas", 56, QFont.Weight.Bold))
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer_lbl.setStyleSheet(f"color: {PALETTE['accent']};")

        root.addWidget(self._status_lbl)
        root.addWidget(self._timer_lbl)

        # ─ Control button ─────────────────────────
        self._btn = _btn("START SESSION")
        self._btn.setFixedWidth(220)
        self._btn.clicked.connect(self._toggle)
        root.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # ─ Internal timer ─────────────────────────
        self._time_left = engine.study_mins * 60
        self._qt_timer  = QTimer()
        self._qt_timer.timeout.connect(self._tick)

    # Public slots called from main app
    def update_frame(self, frame: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, rgb.shape[1], rgb.shape[0],
                     rgb.shape[1] * 3, QImage.Format.Format_RGB888)
        self._vid.setPixmap(
            QPixmap.fromImage(img).scaled(
                640, 360, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        self._refresh_status()

    def refresh_plan(self) -> None:
        self._plan_lbl.setText(
            f"Target: {self._engine.study_mins}m Study / {self._engine.break_mins}m Break")
        self._time_left = self._engine.study_mins * 60
        self._sync_timer_label()

    @property
    def is_active(self) -> bool:
        return self._active

    # ── private ──────────────────────────────────

    def _toggle(self):
        self._active = not self._active
        if self._active:
            self._qt_timer.start(1000)
            self._btn.setText("PAUSE SESSION")
            self._btn.setObjectName("btn_danger")
        else:
            self._qt_timer.stop()
            self._btn.setText("RESUME SESSION")
            self._btn.setObjectName("btn_secondary")
        self._btn.setStyle(self._btn.style())

    def _tick(self):
        if self._time_left > 0:
            self._time_left -= 1
            self._sync_timer_label()
        else:
            self._session_complete()

    def _session_complete(self):
        self._active = False
        self._qt_timer.stop()
        score = self._engine.update_ml_plan()
        storage.save_session(
            self._username, score,
            self._engine.study_mins, self._engine.break_mins
        )
        self.refresh_plan()
        self._btn.setText("START NEXT BLOCK")
        self._btn.setObjectName("")
        self._btn.setStyle(self._btn.style())

    def _sync_timer_label(self):
        m, s = divmod(self._time_left, 60)
        self._timer_lbl.setText(f"{m:02d}:{s:02d}")

    def _refresh_status(self):
        st = self._engine.status
        self._status_lbl.setText(st)
        color = PALETTE["accent"] if "Focused" in st else PALETTE["danger"]
        self._status_lbl.setStyleSheet(f"color: {color};")
