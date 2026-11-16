"""SQLite task store."""
import os
import json
import time
import sqlite3
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "eduforge.db")
_lock = threading.Lock()


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _lock, _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY, created REAL, updated REAL,
            kind TEXT, program TEXT, vid TEXT, status TEXT,
            payload TEXT, result TEXT)""")


def add_task(tid: str, kind: str, program: str, vid: str, payload: dict):
    now = time.time()
    with _lock, _conn() as c:
        c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)",
                  (tid, now, now, kind, program, vid, "queued",
                   json.dumps(payload, ensure_ascii=False), "{}"))


def update_task(tid: str, status: str, result: dict):
    with _lock, _conn() as c:
        c.execute("UPDATE tasks SET status=?, result=?, updated=? WHERE id=?",
                  (status, json.dumps(result, ensure_ascii=False, default=str), time.time(), tid))


def get_task(tid: str):
    with _lock, _conn() as c:
        r = c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
    return _row(r) if r else None


def list_tasks(limit: int = 100):
    with _lock, _conn() as c:
        rows = c.execute("SELECT * FROM tasks ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def _row(r):
    d = dict(r)
    for k in ("payload", "result"):
        try:
            d[k] = json.loads(d[k] or "{}")
        except Exception:
            d[k] = {}
    return d