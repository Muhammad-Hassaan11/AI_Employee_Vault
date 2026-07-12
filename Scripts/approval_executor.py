#!/usr/bin/env python3
"""
Approval Executor for AI Employee Vault - the human-in-the-loop gate.

Scans /Pending_Approval for action files and executes ONLY those a human
has explicitly approved by editing the frontmatter to `status: approved`.

Action file format (created by Atlas via skills):
    ---
    type: email | linkedin_post | facebook_post | instagram_post | tweet
    status: pending          <- human changes to: approved | rejected
    to: someone@example.com  (email only)
    subject: ...             (email only)
    created_at: ...
    ---
    <body: the email text or LinkedIn post text>

Behavior:
    approved  -> execute (send email via SMTP / publish LinkedIn post),
                 then move the file to /Done and log it
    rejected  -> move to /Done marked rejected, log it
    pending   -> leave untouched (waiting for the human)

Run once (for Task Scheduler):
    python Scripts/approval_executor.py
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Watchers"))
from vault_env import VAULT_ROOT, load_env, log, audit  # noqa: E402

PENDING_DIR = VAULT_ROOT / "Pending_Approval"
DONE_DIR = VAULT_ROOT / "Done"


def parse_action_file(path: Path):
    """Parse frontmatter + body. Returns (meta: dict, body: str) or (None, None)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, None
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip().lower()] = value.strip()
    return meta, parts[2].strip()


def parse_post_date(value: str):
    """Parse a post_date string into a date, or None if empty/unparseable.

    Accepts the common formats humans type in the frontmatter. If a value is
    present but can't be parsed, returns None so the item executes rather than
    being silently held forever.
    """
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def execute_email(meta: dict, body: str) -> str:
    """Send an approved email through the same SMTP path as the MCP server."""
    sys.path.insert(0, str(VAULT_ROOT / "MCP"))
    from email_server import send_email  # noqa: E402
    return send_email(meta.get("to", ""), meta.get("subject", "(no subject)"),
                      body, approved=True)


def execute_linkedin(meta: dict, body: str) -> str:
    from linkedin_poster import post_to_linkedin  # same Scripts dir
    return post_to_linkedin(body)


def execute_facebook(meta: dict, body: str) -> str:
    from social_poster import post_facebook  # same Scripts dir
    return post_facebook(body)


def execute_instagram(meta: dict, body: str) -> str:
    from social_poster import post_instagram
    return post_instagram(body, meta.get("image_url", ""))


def execute_tweet(meta: dict, body: str) -> str:
    from social_poster import post_tweet
    return post_tweet(body)


def move_to_done(path: Path, outcome: str) -> None:
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text += f"\n\n## Execution Result\n- {now}: {outcome}\n"
    dest = DONE_DIR / path.name
    dest.write_text(text, encoding="utf-8")
    path.unlink()  # original moved (content preserved in /Done), per handbook


def process_pending() -> int:
    """Process approved/rejected items. Returns number executed."""
    if not PENDING_DIR.exists():
        return 0
    executed = 0

    for path in sorted(PENDING_DIR.glob("*.md")):
        meta, body = parse_action_file(path)
        if meta is None:
            continue
        status = meta.get("status", "pending").lower()
        action_type = meta.get("type", "unknown").lower()

        if status == "rejected":
            move_to_done(path, "REJECTED by human - no action taken")
            log(f"[approval] {path.name}: rejected by human, archived")
            audit("approval_executor", "rejected", file=path.name,
                  action_type=action_type)
            continue
        if status != "approved":
            print(f"[approval] {path.name}: still pending human review")
            continue

        # Approved-but-scheduled: only execute on or after post_date.
        # Future-dated posts stay in place (pending) until their day arrives,
        # so you can safely approve a whole batch at once.
        post_date = parse_post_date(meta.get("post_date", ""))
        if post_date and post_date > datetime.now().date():
            print(f"[approval] {path.name}: approved but scheduled for "
                  f"{post_date.isoformat()}, skipping until then")
            continue

        try:
            if action_type == "email":
                result = execute_email(meta, body)
            elif action_type == "linkedin_post":
                result = execute_linkedin(meta, body)
            elif action_type == "facebook_post":
                result = execute_facebook(meta, body)
            elif action_type == "instagram_post":
                result = execute_instagram(meta, body)
            elif action_type == "tweet":
                result = execute_tweet(meta, body)
            else:
                result = f"ERROR: unknown action type '{action_type}'"
        except Exception as e:
            result = f"ERROR: {e}"

        if result.startswith("SUCCESS"):
            move_to_done(path, result)
            log(f"[approval] Executed {path.name}: {result}")
            audit("approval_executor", "executed", file=path.name,
                  action_type=action_type, result=result[:200])
            executed += 1
        else:
            # Leave in place so the human can see the failure and retry
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n> [!warning] Execution failed {now}: {result}\n")
            log(f"[approval] FAILED {path.name}: {result}")
            audit("approval_executor", "execute", status="failed",
                  file=path.name, action_type=action_type, error=result[:200])

    return executed


def main():
    load_env()
    count = process_pending()
    print(f"[approval] Done. {count} approved action(s) executed.")


if __name__ == "__main__":
    main()
