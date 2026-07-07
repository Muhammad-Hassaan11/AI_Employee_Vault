#!/usr/bin/env python3
"""
LinkedIn Watcher for AI Employee Vault.

Drives the LinkedIn sales-content pipeline:
1. Reads /LinkedIn/Content_Calendar.md for scheduled post topics.
2. When a post is due (its date is today or past) and no task exists yet,
   creates a task in /Needs_Action asking Atlas to draft the post using the
   `linkedin-post` skill. The drafted post goes to /Pending_Approval, and
   after human approval Scripts/approval_executor.py publishes it.

Calendar row format (a Markdown table):
    | Date       | Topic                          | Status  |
    | 2026-07-07 | How automation saves 10h/week  | pending |

The watcher updates Status to `tasked` once a task file has been created.

Run once (for Task Scheduler):
    python Watchers/linkedin_watcher.py
Loop mode:
    python Watchers/linkedin_watcher.py --loop [interval_seconds]
"""

import re
import sys
import time
from datetime import date, datetime

from vault_env import VAULT_ROOT, load_env, create_task_file, log

CALENDAR_FILE = VAULT_ROOT / "LinkedIn" / "Content_Calendar.md"
ROW_RE = re.compile(
    r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*(pending|tasked|posted)\s*\|\s*$",
    re.IGNORECASE,
)


def check_calendar() -> int:
    if not CALENDAR_FILE.exists():
        log(f"[linkedin] Skipped: {CALENDAR_FILE} not found")
        return 0

    lines = CALENDAR_FILE.read_text(encoding="utf-8").splitlines()
    today = date.today()
    created = 0
    updated_lines = []

    for line in lines:
        match = ROW_RE.match(line)
        if match:
            post_date_str, topic, status = match.groups()
            post_date = datetime.strptime(post_date_str, "%Y-%m-%d").date()
            if status.lower() == "pending" and post_date <= today:
                create_task_file(
                    source="linkedin",
                    title=f"Draft LinkedIn post: {topic}",
                    body=(
                        f"**Scheduled date:** {post_date_str}\n"
                        f"**Topic:** {topic}\n\n"
                        f"## Instructions\n\n"
                        f"Use the `linkedin-post` skill to draft a sales-oriented "
                        f"LinkedIn post about this topic for the business.\n"
                        f"Save the draft to /Pending_Approval for human review — "
                        f"NEVER publish directly.\n\n"
                        f"## Suggested Actions\n"
                        f"- [ ] Draft post with the linkedin-post skill\n"
                        f"- [ ] Save draft to /Pending_Approval\n"
                    ),
                    priority="high",
                    task_type="linkedin_post",
                )
                line = line.replace("pending", "tasked", 1)
                created += 1
        updated_lines.append(line)

    if created:
        CALENDAR_FILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        log(f"[linkedin] Created {created} post-drafting task(s)")
    else:
        print("[linkedin] No posts due.")
    return created


def main():
    load_env()
    if "--loop" in sys.argv:
        idx = sys.argv.index("--loop")
        interval = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 3600
        print(f"[linkedin] Watching every {interval}s. Ctrl+C to stop.")
        while True:
            try:
                check_calendar()
            except Exception as e:
                log(f"[linkedin] ERROR: {e}")
            time.sleep(interval)
    else:
        try:
            check_calendar()
        except Exception as e:
            log(f"[linkedin] ERROR: {e}")
            sys.exit(0)


if __name__ == "__main__":
    main()
