# Job Search Agent — Ranked Vacancy Workflow Demo

**Independent portfolio demonstration · Python · FastAPI · SQLite · Explainable Ranking · Docker · pytest**

An offline-first example of a multi-source job-search workflow. The app accepts normalized job listings from **fictional sources**, deduplicates repeat postings, explains skill-based relevance scores, checks publication freshness, flags hiring-region limitations and puts restricted/stale jobs below eligible matches, and lets a human save, dismiss or mark an application as submitted.

> **This is a new portfolio implementation, not a copy of the real private job agent.** All employers, URLs and vacancy descriptions in the demo are fictional, and the candidate profile is generic. It contains no personal information, employer records, Telegram credentials, source configurations, private business logic or real application history.

## Why this demo is useful

- **Multi-source ingestion:** schema validates a common job format for posts from different synthetic boards.
- **Idempotency:** a `(source, external_id)` key prevents repeat intake, while canonical URLs deduplicate mirror posts across sources and strip common tracking parameters.
- **Transparent matching:** 0–100 score with visible explanations for role match, skills, remote format and published salary.
- **Freshness:** the example profile uses a configurable **20-day** window. Older vacancies remain visible but are flagged as stale.
- **Geographic eligibility:** a remote vacancy is *not* automatically worldwide. A mismatch creates a prominent location warning, rather than a false assumption about work authorization.
- **Language:** C1/C2 requirements remain visible as information rather than silently removing roles or claiming advanced language proficiency.
- **Human-controlled applications:** Save, Dismiss and Mark Applied only change **local tracking state**. The agent never submits a real application or sends a message.
- **Optional AI second opinion:** an explicit, on-demand OpenAI structured-output review of a fictional job; it does not change the base score or apply to jobs.
- **Reproducibility:** 10 fictional vacancy examples, 33 automated tests, a Docker setup, a generated Markdown shortlist and GitHub Actions.

The default ranking is **deterministic, not LLM-generated**. It is deliberately explainable and runs without API keys. The optional AI second opinion uses a real OpenAI API call only when explicitly requested. This public demo does not scrape real job boards or use Telegram bots.

## Architecture

```mermaid
flowchart LR
    A[Normalized job inputs] --> B[Pydantic validation]
    B --> C[SQLite idempotency and URL dedup]
    C --> D[Deterministic ranking]
    D --> E[Freshness and hiring geography flags]
    E --> F[Ranked shortlist with reasons]
    F --> G[Manual save / dismiss / applied]
    G --> H[(Local status history)]
```

See [architecture and limitations](docs/architecture.md).

## Run the browser demo

Requires Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**, click **Load sample jobs**, and explore the ranking and filters. Swagger endpoints are available at **http://127.0.0.1:8000/docs**.

Or run in Docker:

```bash
docker compose up --build
```

The sample database persists in a named volume when run with Docker Compose.

### Optional LLM-assisted second opinion

The **AI second opinion** button and `POST /v1/jobs/{id}/ai-review` are optional. Copy `.env.example` to `.env`, add your own `OPENAI_API_KEY`, and restart Docker Compose (or export the environment variable before running Python directly). This makes a **real OpenAI request** with *fictional* vacancy text. Requests cost money. Its structured result is shown separately and does not alter the deterministic match score. With no key, the endpoint returns an explanatory 503 response.

## Generate a Markdown report (no web server needed)

```bash
python -m app.cli --output shortlist.md
```

The generated file contains fictional jobs only. No credentials or internet connection are required.

## API example

```bash
curl -X POST http://127.0.0.1:8000/v1/demo/load
curl http://127.0.0.1:8000/v1/jobs
curl http://127.0.0.1:8000/v1/stats

# Replace 1 with an ID returned from /v1/jobs. This does NOT apply to a job.
curl -X POST http://127.0.0.1:8000/v1/jobs/1/review \
  -H 'Content-Type: application/json' \
  -d '{"status":"saved"}'
```

## Tests

```bash
python -m pytest -q
python -m compileall -q app
python -m app.cli --output shortlist.md
```

GitHub Actions runs the tests and smoke-checks the CLI on every push.

## Real-world next steps

With explicit permission and appropriate terms for each provider: add live job APIs / ATS connectors, source-specific throttling, stronger company/title deduplication, structured job detail extraction, observability and source-health tracking, customizable match profiles, optional human-reviewed AI re-ranking, application-tracking notifications, secure authentication and access control.

**Safety:** This demo API is unauthenticated. Bind to **localhost only**, never deploy it openly. The sample URLs are intentionally fake and should not be considered available jobs.
