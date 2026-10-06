"""Attempts stored locally in SQLite, with the recording kept next to it."""
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path


def question_id(text: str) -> str:
    norm = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha1(norm.encode()).hexdigest()[:12]


class Store:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir)
        (self.dir / "audio").mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "voxiq.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL, "
            "question TEXT NOT NULL, created REAL NOT NULL, audio TEXT NOT NULL, job_description TEXT NOT NULL, result TEXT NOT NULL)"
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS attempts_q ON attempts(question_id)")
        self.db.commit()

    def add(self, question: str, job_description: str, audio_bytes: bytes, suffix: str, result: dict) -> dict:
        qid = question_id(question)
        cur = self.db.execute(
            "INSERT INTO attempts (question_id, question, created, audio, job_description, result) VALUES (?,?,?,?,?,?)",
            (qid, question, time.time(), "", job_description, json.dumps(result)),
        )
        attempt_id = cur.lastrowid
        name = f"{attempt_id}{suffix}"
        (self.dir / "audio" / name).write_bytes(audio_bytes)
        self.db.execute("UPDATE attempts SET audio=? WHERE id=?", (name, attempt_id))
        self.db.commit()
        return self.get(attempt_id)

    def _row(self, r) -> dict:
        return {"id": r["id"], "question_id": r["question_id"], "question": r["question"], "created": r["created"],
                "job_description": r["job_description"], "result": json.loads(r["result"])}

    def get(self, attempt_id: int):
        r = self.db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        return self._row(r) if r else None

    def for_question(self, qid: str) -> list:
        rows = self.db.execute("SELECT * FROM attempts WHERE question_id=? ORDER BY id", (qid,)).fetchall()
        return [self._row(r) for r in rows]

    def audio_path(self, attempt_id: int):
        r = self.db.execute("SELECT audio FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        p = self.dir / "audio" / r["audio"] if r and r["audio"] else None
        return p if p and p.exists() else None

    def delete(self, attempt_id: int) -> bool:
        p = self.audio_path(attempt_id)
        cur = self.db.execute("DELETE FROM attempts WHERE id=?", (attempt_id,))
        self.db.commit()
        if p:
            p.unlink(missing_ok=True)
        return cur.rowcount > 0
