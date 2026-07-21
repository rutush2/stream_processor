import sqlite3
from datetime import datetime

DB_NAME = "telemetry.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                response_time_ms REAL NOT NULL
            )
        """)
        conn.commit()

def insert_log(method: str, path: str, status_code: int, response_time_ms: float):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO api_logs (timestamp, method, path, status_code, response_time_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (datetime.utcnow().isoformat(), method, path, status_code, response_time_ms)
        )
        conn.commit()