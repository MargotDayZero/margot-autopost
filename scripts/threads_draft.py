"""Nightly: write tomorrow's text-only Threads tip and the review-issue body.

Usage: python scripts/threads_draft.py [YYYY-MM-DD]   (defaults to tomorrow, US Eastern)
Outputs threads/<date>.json and threads/<date>.md
"""
from __future__ import annotations

import datetime as dt
import json
import sys

from common import HISTORY, ROOT, load_history, today_et
from threads_generate import generate

THREADS = ROOT / "threads"
THREADS_HISTORY = ROOT / "content" / "threads_history.json"


def main() -> None:
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today_et() + dt.timedelta(days=1)
    THREADS.mkdir(exist_ok=True)
    out = THREADS / f"{day.isoformat()}.json"
    if out.exists():
        print(f"Threads draft for {day} already exists; nothing to do.")
        return

    history = json.loads(THREADS_HISTORY.read_text()) if THREADS_HISTORY.exists() else []
    recent = [h["topic"] for h in history] + [h["topic"] for h in load_history()]
    post = generate(day.weekday(), day.toordinal(), recent, day.strftime("%A, %B %d"))

    record = {"date": day.isoformat(), "topic": post["topic"], "text": post["text"]}
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    history.append({"date": record["date"], "topic": record["topic"]})
    THREADS_HISTORY.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n")

    (THREADS / f"{day.isoformat()}.md").write_text(
        f"**Scheduled to post on Threads {day.strftime('%A, %B %d')} around noon Eastern.**\n\n"
        f"To skip it, just **close this issue**. Do nothing and it posts automatically.\n\n"
        f"**Topic:** {post['topic']}\n\n**Post** ({len(post['text'])} characters):\n\n```\n{post['text']}\n```\n"
    )
    print(f"Drafted Threads post for {day}: {post['topic']}")


if __name__ == "__main__":
    main()
