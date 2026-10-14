"""Offline portfolio dashboard. Operate ONLY on localhost; no auth or job applications."""
import os
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.schemas import CandidateProfile, JobIn, ListedJob, ReviewIn
from app.llm import Analysis, OpenAIJobReviewer
from app.storage import JobStore
from app.seed import seed


def create_app(db_path: str | Path | None = None, profile: CandidateProfile | None = None, ai_reviewer=None) -> FastAPI:
    api = FastAPI(title="Job Search Agent Demo", version="1.0.0")
    store = JobStore(db_path or os.getenv("JOB_DEMO_DB", "./data/jobs.sqlite3"))
    profile = profile or CandidateProfile()

    @api.get("/", include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.post("/v1/demo/load")
    def load():
        return {"inserted": seed(store.path, profile), "stats": store.stats()}

    @api.post("/v1/jobs", response_model=ListedJob)
    def ingest(payload: JobIn):
        record, _ = store.ingest(payload, profile)
        return record

    @api.get("/v1/jobs", response_model=list[ListedJob])
    def jobs(status: Literal["new", "saved", "dismissed", "applied"] | None = None):
        return store.list(status=status)

    @api.get("/v1/stats")
    def stats():
        return store.stats()

    @api.get("/v1/profile", response_model=CandidateProfile)
    def demo_profile():
        return profile

    @api.post("/v1/jobs/{job_id}/review", response_model=ListedJob)
    def review(job_id: int, payload: ReviewIn):
        record = store.review(job_id, payload.status)
        if record is None:
            raise HTTPException(404, "Job not found")
        return record

    @api.post("/v1/jobs/{job_id}/ai-review", response_model=Analysis)
    def ai_review(job_id: int):
        """Explicit opt-in only. This does NOT change the deterministic score."""
        item = store.get(job_id)
        if item is None:
            raise HTTPException(404, "Job not found")
        reviewer = ai_reviewer
        if reviewer is None:
            try:
                reviewer = OpenAIJobReviewer()
            except ValueError:
                raise HTTPException(503, "Optional AI review disabled: no API key configured") from None
        try:
            return reviewer.analyze(item, profile)
        except Exception:
            raise HTTPException(502, "AI provider unavailable; no analysis was recorded") from None

    return api


app = create_app()
