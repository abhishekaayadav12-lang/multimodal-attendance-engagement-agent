import sqlite3
from datetime import datetime, timezone
from config import DB


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                started TEXT NOT NULL,
                ended TEXT
            );

            CREATE TABLE IF NOT EXISTS attendance(
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                track_id TEXT NOT NULL,
                first_seen REAL,
                last_seen REAL,
                duration REAL,
                observations INTEGER,
                status TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS analytics(
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                window REAL,
                visual REAL,
                audio REAL,
                score REAL,
                level TEXT,
                explanation TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            """
        )

        # Upgrade older database files safely.
        cols = {row["name"] for row in c.execute("PRAGMA table_info(attendance)")}
        if "observations" not in cols:
            c.execute("ALTER TABLE attendance ADD COLUMN observations INTEGER DEFAULT 0")

        cols = {row["name"] for row in c.execute("PRAGMA table_info(analytics)")}
        if "level" not in cols:
            c.execute("ALTER TABLE analytics ADD COLUMN level TEXT DEFAULT 'Unknown'")


def create_session(name):
    with db() as c:
        cur = c.execute(
            "INSERT INTO sessions(name,started) VALUES(?,?)",
            (name, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def sessions():
    with db() as c:
        return [
            dict(x)
            for x in c.execute(
                "SELECT * FROM sessions ORDER BY id DESC"
            )
        ]


def save_attendance(session_id, rows):
    with db() as c:
        c.execute("DELETE FROM attendance WHERE session_id=?", (session_id,))
        for r in rows:
            c.execute(
                """
                INSERT INTO attendance(
                    session_id,track_id,first_seen,last_seen,duration,observations,status
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    session_id,
                    r["track_id"],
                    r["first_seen"],
                    r["last_seen"],
                    r["duration_seconds"],
                    r.get("observations", 0),
                    r["status"],
                ),
            )


def attendance(session_id):
    with db() as c:
        return [
            dict(x)
            for x in c.execute(
                """
                SELECT track_id, first_seen, last_seen, duration,
                       observations, status
                FROM attendance
                WHERE session_id=?
                ORDER BY track_id
                """,
                (session_id,),
            )
        ]


def save_analytics(session_id, rows):
    with db() as c:
        c.execute("DELETE FROM analytics WHERE session_id=?", (session_id,))
        for r in rows:
            c.execute(
                """
                INSERT INTO analytics(
                    session_id,window,visual,audio,score,level,explanation
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    session_id,
                    r["window_start"],
                    r.get("visual_activity"),
                    r.get("audio_activity"),
                    r["engagement_score"],
                    r.get("level", "Unknown"),
                    r["explanation"],
                ),
            )


def analytics(session_id):
    with db() as c:
        return [
            dict(x)
            for x in c.execute(
                """
                SELECT window AS window_start,
                       visual AS visual_activity,
                       audio AS audio_activity,
                       score AS engagement_score,
                       level,
                       explanation
                FROM analytics
                WHERE session_id=?
                ORDER BY window
                """,
                (session_id,),
            )
        ]


def delete_session(session_id):
    with db() as c:
        c.execute("DELETE FROM attendance WHERE session_id=?", (session_id,))
        c.execute("DELETE FROM analytics WHERE session_id=?", (session_id,))
        c.execute("DELETE FROM sessions WHERE id=?", (session_id,))
