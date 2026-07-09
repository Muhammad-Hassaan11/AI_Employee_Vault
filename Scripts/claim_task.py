#!/usr/bin/env python3
"""
Claim-by-move helper for the Platinum two-agent (Cloud + Local) setup.

Rule (from the hackathon spec): the first agent to move a task file from
/Needs_Action into /In_Progress/<agent>/ owns it; the other agent must
ignore anything living under another agent's In_Progress folder. Because
the move is committed and pushed by vault_sync, ownership is visible to
both sides and double-work is prevented.

Work-zone specialization:
    Cloud owns:  email triage + draft replies + social post drafts
                 (draft-only; the actual send/post always happens locally)
    Local owns:  approvals, WhatsApp, payments/banking, final send/post

So the cloud agent may only claim tasks whose `source:` frontmatter is in
CLOUD_ALLOWED_SOURCES. The local agent may claim anything.

Usage:
    python Scripts/claim_task.py claim-eligible --agent cloud
    python Scripts/claim_task.py claim Needs_Action/foo.md --agent local
    python Scripts/claim_task.py list
No third-party dependencies - stdlib only.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Watchers"))
from vault_env import VAULT_ROOT, log, audit  # noqa: E402

NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
IN_PROGRESS = VAULT_ROOT / "In_Progress"
AGENTS = ("cloud", "local")

# Sources the CLOUD agent is allowed to claim (its work zone).
# WhatsApp, banking, payments and anything unknown stay with LOCAL.
CLOUD_ALLOWED_SOURCES = {"gmail", "linkedin", "calendar", "file", "filesystem"}


def read_frontmatter_field(path: Path, field: str) -> str:
    """Return a frontmatter value like `source: gmail`, or '' if absent."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(rf"^{field}:\s*(.+)$", text[:2000], re.MULTILINE)
    return match.group(1).strip() if match else ""


def eligible_for(agent: str, task: Path) -> bool:
    if agent == "local":
        return True
    source = read_frontmatter_field(task, "source").lower()
    return source in CLOUD_ALLOWED_SOURCES


def claim(task: Path, agent: str) -> Path | None:
    """Move a task from /Needs_Action to /In_Progress/<agent>/."""
    if not task.exists():
        log(f"[claim] {task.name}: already gone (claimed by the other agent?)")
        return None
    if not eligible_for(agent, task):
        log(f"[claim] {task.name}: outside {agent}'s work zone - skipped")
        return None
    dest_dir = IN_PROGRESS / agent
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / task.name
    shutil.move(str(task), str(dest))
    log(f"[claim] {agent} claimed {task.name}")
    audit("claim_task", "task_claimed", agent=agent, file=task.name)
    return dest


def claim_eligible(agent: str) -> list:
    """Claim every task in /Needs_Action that falls in this agent's zone."""
    claimed = []
    for task in sorted(NEEDS_ACTION.glob("*.md")):
        dest = claim(task, agent)
        if dest:
            claimed.append(dest)
    if not claimed:
        log(f"[claim] Nothing eligible for {agent} in Needs_Action")
    return claimed


def list_claims() -> None:
    for agent in AGENTS:
        files = sorted((IN_PROGRESS / agent).glob("*.md"))
        print(f"In_Progress/{agent}: {len(files)} task(s)")
        for f in files:
            print(f"  - {f.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_claim = sub.add_parser("claim", help="claim one specific task file")
    p_claim.add_argument("task", help="path to a file in Needs_Action")
    p_claim.add_argument("--agent", choices=AGENTS, required=True)

    p_all = sub.add_parser("claim-eligible",
                           help="claim every task in this agent's work zone")
    p_all.add_argument("--agent", choices=AGENTS, required=True)

    sub.add_parser("list", help="show current claims per agent")

    args = parser.parse_args()
    if args.cmd == "claim":
        claim(Path(args.task).resolve(), args.agent)
    elif args.cmd == "claim-eligible":
        claim_eligible(args.agent)
    elif args.cmd == "list":
        list_claims()


if __name__ == "__main__":
    main()
