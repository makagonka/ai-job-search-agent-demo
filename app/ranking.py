"""Transparent, independent rules-based matching. This is NOT LLM scoring."""
import re
from datetime import datetime, timezone
from app.schemas import CandidateProfile, JobIn, MatchResult

TARGET_ROLE_SIGNALS = {
    "ai automation": 28,
    "workflow developer": 28,
    "automation engineer": 26,
    "ai operations": 28,
    "integration engineer": 23,
    "operations manager": 22,
    "project manager": 17,
    "business analyst": 17,
    "technical project manager": 21,
}
TOO_DEEP_SIGNALS = (
    "senior backend engineer", "deep learning researcher", "senior ml engineer",
    "principal software engineer", "research scientist", "kubernetes platform engineer",
)


def has_phrase(haystack: str, needle: str) -> bool:
    phrase = re.escape(needle.casefold().strip())
    return bool(re.search(r"(?<!\w)" + phrase + r"(?!\w)", haystack.casefold()))


def age_in_days(published: datetime, now: datetime) -> int:
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return (now.astimezone(timezone.utc).date() - published.astimezone(timezone.utc).date()).days


def rank_job(job: JobIn, profile: CandidateProfile, now: datetime | None = None) -> MatchResult:
    now = now or datetime.now(timezone.utc)
    age = age_in_days(job.published_at, now)
    title = job.title.casefold()
    content = (job.title + " " + job.description).casefold()
    reasons = []
    score = 30

    role_hits = [(role, bonus) for role, bonus in TARGET_ROLE_SIGNALS.items()
                 if has_phrase(title, role) and any(has_phrase(role, wanted) or has_phrase(wanted, role)
                                                   for wanted in profile.target_roles)]
    if role_hits:
        role, bonus = max(role_hits, key=lambda x: x[1])
        score += bonus
        reasons.append(f"Target role: {role} (+{bonus})")
    else:
        score -= 18
        reasons.append("No direct target role in title (-18)")

    skill_hits = sorted({skill for skill in profile.target_skills if has_phrase(content, skill)})
    bonus = min(len(skill_hits) * 5, 25)
    score += bonus
    if skill_hits:
        reasons.append(f"Skill overlap: {', '.join(skill_hits)} (+{bonus})")

    if profile.prefer_remote:
        score += 8 if job.remote else -25
        reasons.append("Remote role (+8)" if job.remote else "On-site role (-25)")

    if any(has_phrase(title, term) for term in TOO_DEEP_SIGNALS):
        score -= 32
        reasons.append("Specialist role outside target scope (-32)")

    if profile.minimum_salary_rub is not None and job.minimum_salary_rub is not None:
        if job.minimum_salary_rub >= profile.minimum_salary_rub:
            score += 6
            reasons.append("Published salary meets target (+6)")
        else:
            score -= 10
            reasons.append("Published salary below target (-10)")
    else:
        reasons.append("Salary not comparable or not specified")

    geography_warning = None
    regions = {x.casefold() for x in job.hiring_regions}
    eligible = {x.casefold() for x in profile.eligible_regions}
    if regions and "worldwide" not in regions and not (regions & eligible):
        geography_warning = "Hiring locations do not match the example candidate's eligibility; verify before applying"
        reasons.append("Location eligibility needs verification (hard warning)")

    english_note = None
    if job.english_requirement:
        english_note = f"English requirement stated: {job.english_requirement}. Check communication expectations; no automatic score penalty."

    score = max(0, min(100, score))
    if age < 0:
        decision = "future_date"
        reasons.append("Publication date appears to be in the future")
    elif age > profile.freshness_days:
        decision = "stale"
        reasons.append(f"Posted {age} days ago (limit: {profile.freshness_days})")
    elif geography_warning:
        decision = "geo_restricted"
    elif score >= 75:
        decision = "strong"
    elif score >= profile.min_score:
        decision = "review"
    else:
        decision = "low"
    return MatchResult(score=score, decision=decision, reasons=reasons,
                       age_days=age, geography_warning=geography_warning, english_note=english_note)
