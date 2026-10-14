"""SQLite event history and manual application status; no external applications."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from app.schemas import CandidateProfile, JobIn, ListedJob, MatchResult
from app.ranking import rank_job

TRACKING_QUERY_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(sorted((key, value) for key, value in parse_qsl(parts.query)
                             if key.casefold() not in TRACKING_QUERY_KEYS))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", query, ""))


class JobStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source TEXT NOT NULL, external_id TEXT NOT NULL,
                  canonical_url TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
                  evaluation TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
                  first_seen TEXT NOT NULL,
                  UNIQUE(source,external_id)
                );
                CREATE TABLE IF NOT EXISTS reviews (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL,
                  status TEXT NOT NULL, changed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            """)

    def connect(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def _record(row) -> ListedJob:
        data = json.loads(row["payload"])
        data.update(json.loads(row["evaluation"]))
        return ListedJob(id=row["id"], status=row["status"], first_seen=row["first_seen"], **data)

    def ingest(self, job: JobIn, profile: CandidateProfile, now: datetime | None = None) -> tuple[ListedJob, bool]:
        now = now or datetime.now(timezone.utc)
        evaluation: MatchResult = rank_job(job, profile, now)
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute(
                "SELECT * FROM jobs WHERE (source=? AND external_id=?) OR canonical_url=? LIMIT 1",
                (job.source, job.external_id, canonical_url(job.url)),
            ).fetchone()
            if existing:
                return self._record(existing), False
            cursor = con.execute("""
                INSERT INTO jobs(source,external_id,canonical_url,payload,evaluation,first_seen)
                VALUES(?,?,?,?,?,?)
                """, (job.source, job.external_id, canonical_url(job.url),
                      job.model_dump_json(), evaluation.model_dump_json(), now.isoformat()))
            row = con.execute("SELECT * FROM jobs WHERE id=?", (cursor.lastrowid,)).fetchone()
            return self._record(row), True

    def get(self, job_id: int) -> ListedJob | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._record(row) if row else None

    def list(self, status: str | None = None) -> list[ListedJob]:
        with self.connect() as con:
            if status:
                rows = con.execute("SELECT * FROM jobs WHERE status=?", (status,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM jobs").fetchall()
        priority = {"strong": 0, "review": 1, "low": 2,
                    "geo_restricted": 3, "stale": 4, "future_date": 5}
        return sorted((self._record(row) for row in rows),
                      key=lambda x: (priority.get(x.decision, 6), -x.score, x.id))

    def review(self, job_id: int, status: str) -> ListedJob | None:
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                return None
            con.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
            con.execute("INSERT INTO reviews(job_id,status,changed_at) VALUES(?,?,?)",
                        (job_id, status, datetime.now(timezone.utc).isoformat()))
        return self.get(job_id)

    def stats(self):
        rows = self.list()
        return {
            "total": len(rows),
            "strong": sum(x.decision == "strong" for x in rows),
            "review": sum(x.decision == "review" for x in rows),
            "geo_restricted": sum(x.decision == "geo_restricted" for x in rows),
            "stale": sum(x.decision == "stale" for x in rows),
            "saved": sum(x.status == "saved" for x in rows),
            "applied": sum(x.status == "applied" for x in rows),
        }
