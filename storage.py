"""
storage.py — StudyBuddy AI
SQLite persistence layer. All DB calls live here; nothing else touches the DB directly.
"""

import sqlite3
import hashlib
import secrets
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "StudyBuddy.db"


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _hash(password: str, salt: str) -> str:
    """SHA-256 hash of password + salt."""
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _new_salt() -> str:
    return secrets.token_hex(16)


# ──────────────────────────────────────────────
# Schema initialisation
# ──────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't exist yet."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username        TEXT PRIMARY KEY,
                password_hash   TEXT NOT NULL,
                salt            TEXT NOT NULL,
                full_name       TEXT DEFAULT '',
                email           TEXT DEFAULT '',
                study_goal_hrs  REAL DEFAULT 2.0,
                avatar_color    TEXT DEFAULT '#10B981',
                created_at      TEXT DEFAULT (date('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                date        TEXT NOT NULL,
                focus_score REAL NOT NULL,
                study_mins  INTEGER NOT NULL,
                break_mins  INTEGER NOT NULL,
                notes       TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS security_questions (
                username    TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
                question    TEXT NOT NULL,
                answer_hash TEXT NOT NULL,
                salt        TEXT NOT NULL
            );
        """)


# ──────────────────────────────────────────────
# User auth
# ──────────────────────────────────────────────

def register_user(username: str, password: str,
                  full_name: str = "", email: str = "") -> tuple[bool, str]:
    """
    Returns (success, message).
    Fails if username already exists.
    """
    with _connect() as conn:
        existing = conn.execute(
            "SELECT username FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return False, "Username already taken."

        salt = _new_salt()
        pw_hash = _hash(password, salt)
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, full_name, email) VALUES (?,?,?,?,?)",
            (username, pw_hash, salt, full_name, email)
        )
    return True, "Account created."


def verify_login(username: str, password: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not row:
        return False, "Username not found."
    if _hash(password, row["salt"]) != row["password_hash"]:
        return False, "Incorrect password."
    return True, "Login successful."


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    ok, msg = verify_login(username, old_password)
    if not ok:
        return False, "Current password is wrong."
    salt = _new_salt()
    pw_hash = _hash(new_password, salt)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE username=?",
            (pw_hash, salt, username)
        )
    return True, "Password changed successfully."


def reset_password_via_security(username: str, answer: str, new_password: str) -> tuple[bool, str]:
    """Reset password using security-question answer."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT answer_hash, salt FROM security_questions WHERE username=?", (username,)
        ).fetchone()
        if not row:
            return False, "No security question set for this account."
        if _hash(answer.strip().lower(), row["salt"]) != row["answer_hash"]:
            return False, "Wrong answer."
        salt = _new_salt()
        pw_hash = _hash(new_password, salt)
        conn.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE username=?",
            (pw_hash, salt, username)
        )
    return True, "Password reset successful."


# ──────────────────────────────────────────────
# Security questions
# ──────────────────────────────────────────────

SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What city were you born in?",
    "What is your mother's maiden name?",
    "What was the name of your first school?",
    "What is your favourite book?",
]


def set_security_question(username: str, question: str, answer: str) -> None:
    salt = _new_salt()
    answer_hash = _hash(answer.strip().lower(), salt)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO security_questions (username, question, answer_hash, salt)
            VALUES (?,?,?,?)
            ON CONFLICT(username) DO UPDATE SET
                question=excluded.question,
                answer_hash=excluded.answer_hash,
                salt=excluded.salt
        """, (username, question, answer_hash, salt))


def get_security_question(username: str) -> str | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT question FROM security_questions WHERE username=?", (username,)
        ).fetchone()
    return row["question"] if row else None


# ──────────────────────────────────────────────
# Profile
# ──────────────────────────────────────────────

def get_profile(username: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT username, full_name, email, study_goal_hrs, avatar_color, created_at FROM users WHERE username=?",
            (username,)
        ).fetchone()
    return dict(row) if row else None


def update_profile(username: str, full_name: str, email: str,
                   study_goal_hrs: float, avatar_color: str) -> tuple[bool, str]:
    with _connect() as conn:
        conn.execute("""
            UPDATE users SET full_name=?, email=?, study_goal_hrs=?, avatar_color=?
            WHERE username=?
        """, (full_name, email, study_goal_hrs, avatar_color, username))
    return True, "Profile updated."


# ──────────────────────────────────────────────
# Sessions / Analytics
# ──────────────────────────────────────────────

def save_session(username: str, focus_score: float,
                 study_mins: int, break_mins: int, notes: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (username, date, focus_score, study_mins, break_mins, notes) VALUES (?,?,?,?,?,?)",
            (username, str(datetime.date.today()), round(focus_score, 1), study_mins, break_mins, notes)
        )


def get_recent_sessions(username: str, limit: int = 10) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT date, focus_score, study_mins, break_mins, notes
            FROM sessions WHERE username=?
            ORDER BY id DESC LIMIT ?
        """, (username, limit)).fetchall()
    return [dict(r) for r in rows]


def get_stats_summary(username: str) -> dict:
    with _connect() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)            AS total_sessions,
                ROUND(AVG(focus_score), 1) AS avg_focus,
                SUM(study_mins)     AS total_study_mins,
                MAX(focus_score)    AS best_score,
                MIN(focus_score)    AS worst_score
            FROM sessions WHERE username=?
        """, (username,)).fetchone()

        streak_row = conn.execute("""
            SELECT COUNT(DISTINCT date) AS days_active
            FROM sessions
            WHERE username=? AND date >= date('now', '-7 days')
        """, (username,)).fetchone()

    summary = dict(row) if row else {}
    summary["days_active_week"] = streak_row["days_active"] if streak_row else 0
    return summary


def delete_all_sessions(username: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE username=?", (username,))


def delete_account(username: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM users WHERE username=?", (username,))
