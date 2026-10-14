"""Run an entirely offline demo and produce a transparent Markdown shortlist."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from app.schemas import CandidateProfile
from app.seed import seed
from app.storage import JobStore


def report(rows):
    lines = ["# Fictional Job Agent — Ranked Shortlist", "", "All roles and employers below are SYNTHETIC. No applications were submitted.", ""]
    for item in rows:
        lines += [f"## {item.score}/100 · {item.title} — {item.company}",
                  f"Decision: **{item.decision}** · {item.age_days} days old · {item.source}",
                  f"Remote: {'yes' if item.remote else 'no'} · Hiring regions: {', '.join(item.hiring_regions) or 'unspecified'}",
                  *(f"- {reason}" for reason in item.reasons), ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Offline fictional job search portfolio demo")
    parser.add_argument("--output", help="Write ranked Markdown report to this path")
    opts = parser.parse_args()
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "job_demo.sqlite3"
        seed(str(path), CandidateProfile())
        text = report(JobStore(path).list())
        if opts.output:
            Path(opts.output).write_text(text, encoding="utf-8")
            print(f"Demo report written: {opts.output}")
        else:
            print(text)


if __name__ == "__main__":
    main()
