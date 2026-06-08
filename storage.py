"""
storage.py — StudyBuddy AI
SQLite persistence layer. All DB calls live here; nothing else touches the DB directly.
"""

import sqlite3
import secrets
import datetime
import json
from pathlib import Path

import bcrypt

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


def _hash_password(password: str) -> str:
    """bcrypt hash of password. Salt is embedded in the returned string."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def _hash_answer(answer: str) -> str:
    """bcrypt hash of a security-question answer (normalised to lowercase)."""
    return bcrypt.hashpw(answer.strip().lower().encode(), bcrypt.gensalt()).decode()


def _verify_answer(answer: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(answer.strip().lower().encode(), hashed.encode())
    except Exception:
        return False


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
                answer_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_tokens (
                token       TEXT PRIMARY KEY,
                username    TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                created_at  TEXT NOT NULL
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

        pw_hash = _hash_password(password)
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, email) VALUES (?,?,?,?)",
            (username, pw_hash, full_name, email)
        )
    return True, "Account created."


def verify_login(username: str, password: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not row:
        return False, "Username not found."
    if not _verify_password(password, row["password_hash"]):
        return False, "Incorrect password."
    return True, "Login successful."


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    ok, msg = verify_login(username, old_password)
    if not ok:
        return False, "Current password is wrong."
    pw_hash = _hash_password(new_password)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (pw_hash, username)
        )
    return True, "Password changed successfully."


def reset_password_via_security(username: str, answer: str, new_password: str) -> tuple[bool, str]:
    """Reset password using security-question answer."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT answer_hash FROM security_questions WHERE username=?", (username,)
        ).fetchone()
        if not row:
            return False, "No security question set for this account."
        if not _verify_answer(answer, row["answer_hash"]):
            return False, "Wrong answer."
        pw_hash = _hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (pw_hash, username)
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
    answer_hash = _hash_answer(answer)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO security_questions (username, question, answer_hash)
            VALUES (?,?,?)
            ON CONFLICT(username) DO UPDATE SET
                question=excluded.question,
                answer_hash=excluded.answer_hash
        """, (username, question, answer_hash))


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


# ──────────────────────────────────────────────
# Session Token Management
# ──────────────────────────────────────────────

SESSION_FILE_PATH = DB_PATH.parent / "session.json"

# Maximum age for a persisted login token (30 days).
_TOKEN_MAX_AGE_DAYS = 30


def save_session_token(username: str) -> None:
    """Generate a random opaque token, persist it in the DB and in a local file."""
    token = secrets.token_hex(32)
    created_at = datetime.datetime.utcnow().isoformat()
    with _connect() as conn:
        # Remove any previous token for this user before inserting the new one.
        conn.execute("DELETE FROM session_tokens WHERE username=?", (username,))
        conn.execute(
            "INSERT INTO session_tokens (token, username, created_at) VALUES (?,?,?)",
            (token, username, created_at),
        )
    SESSION_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_FILE_PATH, "w") as f:
        json.dump({"token": token}, f)


def load_session_token() -> str | None:
    """
    Read the token from disk, look it up in the DB, and return the username
    if it is valid and not expired.  Returns None otherwise.
    """
    if not SESSION_FILE_PATH.exists():
        return None
    try:
        with open(SESSION_FILE_PATH, "r") as f:
            data = json.load(f)
        token = data.get("token")
        if not token:
            return None
        with _connect() as conn:
            row = conn.execute(
                "SELECT username, created_at FROM session_tokens WHERE token=?",
                (token,),
            ).fetchone()
        if not row:
            return None
        # Reject tokens older than _TOKEN_MAX_AGE_DAYS.
        created = datetime.datetime.fromisoformat(row["created_at"])
        age = datetime.datetime.utcnow() - created
        if age.days > _TOKEN_MAX_AGE_DAYS:
            clear_session_token()
            return None
        return row["username"]
    except Exception:
        return None


def clear_session_token() -> None:
    """Delete the token from both disk and the DB."""
    if SESSION_FILE_PATH.exists():
        try:
            # Read the token so we can remove the DB row too.
            with open(SESSION_FILE_PATH, "r") as f:
                data = json.load(f)
            token = data.get("token")
            if token:
                with _connect() as conn:
                    conn.execute("DELETE FROM session_tokens WHERE token=?", (token,))
        except Exception:
            pass
        try:
            SESSION_FILE_PATH.unlink()
        except Exception:
            pass
        

# ===================== V2 ANALYTICS =====================

def _ensure_v2_schema() -> None:
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS study_analytics (
            username TEXT PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            longest_session_mins INTEGER DEFAULT 0,
            last_study_date TEXT,
            FOREIGN KEY(username) REFERENCES users(username) ON DELETE CASCADE
        )
        """)

        # Ensure session_tokens table exists (may be missing on older DBs).
        conn.execute("""
        CREATE TABLE IF NOT EXISTS session_tokens (
            token       TEXT PRIMARY KEY,
            username    TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
            created_at  TEXT NOT NULL
        )
        """)

        for stmt in [
            "ALTER TABLE sessions ADD COLUMN fatigue_events INTEGER DEFAULT 0",
            "ALTER TABLE sessions ADD COLUMN ended_reason TEXT DEFAULT 'Completed'",
            "ALTER TABLE sessions ADD COLUMN session_type TEXT DEFAULT 'Standard'",
        ]:
            try:
                conn.execute(stmt)
            except Exception:
                pass

        _migrate_drop_salt_columns(conn)


def _migrate_drop_salt_columns(conn: sqlite3.Connection) -> None:
    """
    Remove the legacy `salt` columns from `users` and `security_questions`
    if they still exist (databases created before the bcrypt migration).

    SQLite does not support DROP COLUMN before version 3.35, so we use the
    standard rename-create-copy-drop pattern which works on all versions.
    The migration is idempotent: if the column is already absent it does nothing.
    """
    # ── users table ──────────────────────────────────────────────────────────
    user_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "salt" in user_cols:
        conn.executescript("""
            PRAGMA foreign_keys = OFF;

            CREATE TABLE IF NOT EXISTS users_new (
                username        TEXT PRIMARY KEY,
                password_hash   TEXT NOT NULL,
                full_name       TEXT DEFAULT '',
                email           TEXT DEFAULT '',
                study_goal_hrs  REAL DEFAULT 2.0,
                avatar_color    TEXT DEFAULT '#10B981',
                created_at      TEXT DEFAULT (date('now'))
            );

            INSERT INTO users_new
                (username, password_hash, full_name, email,
                 study_goal_hrs, avatar_color, created_at)
            SELECT  username, password_hash, full_name, email,
                    study_goal_hrs, avatar_color, created_at
            FROM    users;

            DROP TABLE users;
            ALTER TABLE users_new RENAME TO users;

            PRAGMA foreign_keys = ON;
        """)

    # ── security_questions table ──────────────────────────────────────────────
    sq_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(security_questions)").fetchall()
    }
    if "salt" in sq_cols:
        conn.executescript("""
            PRAGMA foreign_keys = OFF;

            CREATE TABLE IF NOT EXISTS security_questions_new (
                username    TEXT PRIMARY KEY
                                REFERENCES users(username) ON DELETE CASCADE,
                question    TEXT NOT NULL,
                answer_hash TEXT NOT NULL
            );

            INSERT INTO security_questions_new
                (username, question, answer_hash)
            SELECT  username, question, answer_hash
            FROM    security_questions;

            DROP TABLE security_questions;
            ALTER TABLE security_questions_new RENAME TO security_questions;

            PRAGMA foreign_keys = ON;
        """)

_ensure_v2_schema()

def get_streak_info(username:str)->dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT current_streak,best_streak FROM study_analytics WHERE username=?",
            (username,)
        ).fetchone()
    if not row:
        return {"current_streak":0,"best_streak":0}
    return dict(row)

def update_streak(username:str)->None:
    today = str(datetime.date.today())
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM study_analytics WHERE username=?",
            (username,)
        ).fetchone()

        if not row:
            conn.execute("""
                INSERT INTO study_analytics
                (username,current_streak,best_streak,last_study_date)
                VALUES (?,?,?,?)
            """,(username,1,1,today))
            return

        last = row["last_study_date"]
        current = row["current_streak"]

        if last == today:
            return

        diff = (datetime.date.fromisoformat(today) -
                datetime.date.fromisoformat(last)).days if last else 999

        if diff == 1:
            current += 1
        else:
            current = 1

        best = max(current,row["best_streak"])

        conn.execute("""
            UPDATE study_analytics
            SET current_streak=?,
                best_streak=?,
                last_study_date=?
            WHERE username=?
        """,(current,best,today,username))

def get_weekly_focus_trend(username:str)->list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT date,
                   ROUND(AVG(focus_score),1) as focus
            FROM sessions
            WHERE username=?
            AND date >= date('now','-7 days')
            GROUP BY date
            ORDER BY date
        """,(username,)).fetchall()
    return [dict(r) for r in rows]

def generate_insight(username:str)->str:
    s = get_stats_summary(username)
    avg = s.get("avg_focus") or 0

    if avg >= 90:
        return "Excellent focus consistency. Keep your current routine."
    if avg >= 75:
        return "Good progress. Short breaks may improve focus further."
    if avg > 0:
        return "Focus is improving. Try reducing distractions before sessions."
    return "Complete a study session to unlock personalised insights."


def get_longest_session(username:str)->int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT MAX(study_mins) AS longest FROM sessions WHERE username=?",
            (username,)
        ).fetchone()
    return int((row["longest"] or 0))

def get_total_hours(username:str)->float:
    with _connect() as conn:
        row = conn.execute(
            "SELECT SUM(study_mins) AS mins FROM sessions WHERE username=?",
            (username,)
        ).fetchone()
    return round((row["mins"] or 0)/60,1)