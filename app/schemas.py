"""Schemas for synthetic job postings and configurable candidate matching."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class JobIn(BaseModel):
    source: str = Field(min_length=2, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    external_id: str = Field(min_length=2, max_length=70)
    url: str = Field(pattern=r"^https://", max_length=500)
    title: str = Field(min_length=3, max_length=160)
    company: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    remote: bool
    hiring_regions: list[str] = Field(default_factory=list, max_length=8)
    published_at: datetime
    minimum_salary_rub: int | None = Field(default=None, ge=0)
    english_requirement: str | None = Field(default=None, max_length=60)


class CandidateProfile(BaseModel):
    target_roles: list[str] = Field(default_factory=lambda: [
        "ai automation", "workflow developer", "operations manager", "automation engineer",
    ], min_length=1)
    target_skills: list[str] = Field(default_factory=lambda: [
        "python", "api", "docker", "llm", "automation", "crm", "integration", "workflow",
    ])
    eligible_regions: list[str] = Field(default_factory=lambda: ["Worldwide", "Europe"])
    prefer_remote: bool = True
    minimum_salary_rub: int | None = Field(default=100000, ge=0)
    freshness_days: int = Field(default=20, ge=1, le=90)
    min_score: int = Field(default=50, ge=0, le=100)


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100)
    decision: Literal["strong", "review", "low", "stale", "future_date", "geo_restricted"]
    reasons: list[str]
    age_days: int
    geography_warning: str | None = None
    english_note: str | None = None


class ListedJob(BaseModel):
    id: int
    source: str
    external_id: str
    url: str
    title: str
    company: str
    description: str
    remote: bool
    hiring_regions: list[str]
    published_at: str
    minimum_salary_rub: int | None
    english_requirement: str | None
    score: int
    decision: str
    reasons: list[str]
    age_days: int
    geography_warning: str | None
    english_note: str | None
    status: str
    first_seen: str


class ReviewIn(BaseModel):
    status: Literal["saved", "dismissed", "applied"]
