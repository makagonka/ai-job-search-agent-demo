"""Generate dated, fictional job posts. Every company and URL is invented."""
from datetime import datetime, timedelta, timezone
from app.schemas import CandidateProfile, JobIn
from app.storage import JobStore

EXAMPLES = [
    ("board_a", "001", "AI Automation Engineer", "Example Horizon", "Build Python automation, REST API and workflow integrations using Docker and LLM tools.", True, ["Worldwide"], 3, 180000, "B2"),
    ("board_b", "002", "Workflow Developer", "Sample Systems", "Create CRM workflow automation with Python, Docker and REST API for client operations.", True, ["Europe"], 2, 150000, "C1"),
    ("board_c", "003", "AI Operations Manager", "Demo Dynamics", "Lead automation projects with LLM classification, API integrations and process improvement.", True, ["Europe"], 7, None, None),
    ("board_a", "004", "Senior Backend Engineer", "Fictional Backend", "Develop low level databases, Golang, Kubernetes and distributed compute.", True, ["Worldwide"], 5, 280000, None),
    ("board_d", "005", "Workflow Developer", "Mock Pacific", "Develop automation, Python API and CRM systems for customers based in the USA.", True, ["United States only"], 2, 160000, "C1"),
    ("board_c", "006", "Automation Engineer", "Prototype Works", "Implement Python workflow and API integration services.", False, ["Europe"], 4, 140000, None),
    ("board_d", "007", "Project Manager", "Synthetic Projects", "Plan and deliver IT process automation projects integrating CRM systems.", True, ["Europe"], 12, 125000, "B2"),
    ("board_b", "008", "AI Automation Engineer", "Old Sample Corp", "Build Python automation and Docker services with API integration.", True, ["Worldwide"], 26, 175000, None),
    ("board_e", "009", "Machine Learning Research Scientist", "Hypothetical AI Lab", "Conduct deep learning research using PhD-level numerical modelling.", True, ["Worldwide"], 8, 300000, None),
    ("board_f", "010", "AI Workflow Developer", "Illustration Digital", "Automate internal reporting and CRM approval workflows with Python and APIs.", True, ["Worldwide"], 1, None, "English fluent"),
]


def examples(now: datetime | None = None) -> list[JobIn]:
    now = now or datetime.now(timezone.utc)
    return [JobIn(source=source, external_id=eid,
                  url=f"https://jobs.example.org/{eid}", title=title, company=company,
                  description=description, remote=remote, hiring_regions=regions,
                  published_at=now - timedelta(days=age), minimum_salary_rub=salary,
                  english_requirement=english)
            for source,eid,title,company,description,remote,regions,age,salary,english in EXAMPLES]


def seed(path: str, profile: CandidateProfile | None = None, now: datetime | None = None) -> int:
    store = JobStore(path)
    profile = profile or CandidateProfile()
    count = 0
    for item in examples(now):
        _, inserted = store.ingest(item, profile, now=now)
        count += inserted
    return count
