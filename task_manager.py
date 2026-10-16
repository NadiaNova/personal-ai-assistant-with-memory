
"""Persistent task, reminder, and notes storage using SQLite."""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "assistant_tasks.db"


def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_at TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def add_task(title, due_at=None):
    title = title.strip()
    if not title:
        raise ValueError("Task title cannot be empty.")

    with connect() as conn:
        cursor = conn.execute(
            """INSERT INTO tasks (title, due_at, created_at)
               VALUES (?, ?, ?)""",
            (title, due_at, datetime.now().isoformat(timespec="seconds")),
        )
        return cursor.lastrowid


def get_tasks(show_completed=True):
    query = "SELECT * FROM tasks"
    if not show_completed:
        query += " WHERE completed = 0"
    query += " ORDER BY completed ASC, due_at IS NULL ASC, due_at ASC, id DESC"

    with connect() as conn:
        return [dict(row) for row in conn.execute(query).fetchall()]


def complete_task(task_id, completed=True):
    with connect() as conn:
        conn.execute(
            "UPDATE tasks SET completed = ? WHERE id = ?",
            (1 if completed else 0, task_id),
        )


def delete_task(task_id):
    with connect() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def add_note(title, content):
    title = title.strip()
    content = content.strip()

    if not title or not content:
        raise ValueError("Both note title and content are required.")

    with connect() as conn:
        cursor = conn.execute(
            """INSERT INTO notes (title, content, created_at)
               VALUES (?, ?, ?)""",
            (
                title,
                content,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cursor.lastrowid


def get_notes():
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM notes ORDER BY id DESC"
            ).fetchall()
        ]


def delete_note(note_id):
    with connect() as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))


def get_due_reminders():
    """Return all unfinished tasks that have a scheduled due date."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT * FROM tasks
               WHERE completed = 0
                 AND due_at IS NOT NULL
               ORDER BY due_at ASC""",
        ).fetchall()

        return [dict(row) for row in rows]


initialize_db()