import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "healthify.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('patient', 'doctor', 'admin')),
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'pending', 'rejected')),
            created_at TEXT NOT NULL
        )
    """)

    # Seed admin account if not present
    cursor.execute("SELECT id FROM users WHERE email = 'admin@healthify.com'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (name, email, password, role, status, created_at)
            VALUES (?, ?, ?, 'admin', 'active', ?)
        """, ("Admin", "admin@healthify.com", hash_password("admin123"), datetime.now().isoformat()))

    conn.commit()
    conn.close()


def create_user(name: str, email: str, password: str, role: str) -> tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        status = "pending" if role == "doctor" else "active"
        normalized_name = name.strip().title()
        normalized_email = email.strip().lower()
        cursor.execute("""
            INSERT INTO users (name, email, password, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (normalized_name, normalized_email, hash_password(password), role, status, datetime.now().isoformat()))
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        conn.close()


def authenticate_user(email: str, password: str, role: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    normalized_email = email.strip().lower()
    cursor.execute("""
        SELECT * FROM users WHERE email = ? AND password = ? AND role = ?
    """, (normalized_email, hash_password(password), role))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role != 'admin' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_doctors() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role = 'doctor' AND status = 'pending' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_status(user_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
