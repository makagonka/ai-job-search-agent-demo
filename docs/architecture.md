# Architecture and intentional limitations

This project is **original portfolio code**, written separately from any commercial or privately configured system. It uses artificial sources, companies, URLs and profile settings.

## Components

| Part | Responsibility |
|---|---|
| `app/schemas.py` | Common input contract, generic fictional profile and validation |
| `app/seed.py` | Ten dynamically dated, fictional vacancies from six invented boards |
| `app/ranking.py` | Deterministic role/skill matching and transparent 0–100 score |
| `app/storage.py` | SQLite idempotent ingestion, canonical URL deduplication and manual status history |
| `app/api.py` | Local REST API and demonstration dashboard |
| `app/cli.py` | Reproducible Markdown shortlist without an internet connection |
| `tests/` | Automated API, ranking, state, deduplication and security-boundary checks |

## Key decisions

- **No automated application:** `applied` is a status manually selected *after* a real user applies elsewhere, not an API integration.
- **Remote is not worldwide:** hiring regions are separate from the `remote` flag; possible eligibility mismatches are explicitly highlighted.
- **Language is a requirement note, not a candidate self-assessment.** An English requirement does not increase or decrease the score automatically.
- **Outdated jobs:** stale/future-dated posts retain their history and are tagged accordingly; they are not silently mixed into the strong-match lane.
- **Dedupe:** same source/external ID and normalized URL are idempotent. This is not full semantic deduplication of mirror ads with entirely different URLs.
- **AI boundary:** the shortlist and score are deterministic and explainable. A separate, optional OpenAI analysis can be requested manually with a user-provided API key; it does not silently re-rank results and is not verified against a real hiring process.
- **No real data or API keys:** every sample comes from `jobs.example.org`, a deliberately fictitious domain.
- **No network collection:** live crawling is deliberately out of scope; adding it requires permission, rate limits, compliance with source terms and integration tests.
- **SQLite + a single local process:** sufficient for demonstration. Production systems need proper auth, migration strategy, queuing, retention controls, deletion, backups, structured source metadata and source-specific monitoring.

## Relevant future features

Live public/ATS connectors, configurable scoring calibration from labelled feedback, separate skills/role vocabulary per locale, semantic repost detection with careful precision measurement, location and employment-authorization matching, scheduled notification digests, and human-in-the-loop approval controls.
