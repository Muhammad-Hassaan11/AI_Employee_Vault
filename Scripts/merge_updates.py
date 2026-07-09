#!/usr/bin/env python3
"""
Merge cloud updates into Dashboard.md - the Platinum single-writer rule.

Only the LOCAL agent may edit Dashboard.md. The Cloud agent instead drops
files into /Updates/:

    UPDATE_*.md  - one-line-ish activity notes ("drafted reply to X").
                   Merged into Dashboard's "## Recent Activity" section,
                   then archived to /Done (never deleted).
    HEALTH_*.md  - health snapshots, overwritten in place by the cloud
                   health monitor. Their "Status:" line is mirrored into
                   Dashboard's "## Alerts" section; the file stays put.

Run on the local machine (run_employee.ps1 calls it every cycle):
    python Scripts/merge_updates.py
No third-party dependencies - stdlib only.
"""

import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Watchers"))
from vault_env import VAULT_ROOT, log, audit  # noqa: E402

UPDATES = VAULT_ROOT / "Updates"
DASHBOARD = VAULT_ROOT / "Dashboard.md"
DONE = VAULT_ROOT / "Done" / "Updates"


def first_summary_line(text: str) -> str:
    """First non-empty, non-frontmatter, non-heading line of an update."""
    text = text.lstrip("﻿")  # BOM (e.g. PowerShell utf8 writes)
    body = re.sub(r"\A---\r?\n.*?\r?\n---\r?\n", "", text, flags=re.DOTALL)
    for line in body.splitlines():
        line = line.strip().lstrip("-# ").strip()
        if line:
            return line
    return "(empty update)"


def insert_after_heading(dashboard: str, heading: str, lines: list) -> str:
    """Insert bullet lines directly under `## <heading>`."""
    pattern = rf"(^## {re.escape(heading)}\s*\n)"
    block = "\n".join(lines) + "\n"
    if re.search(pattern, dashboard, re.MULTILINE):
        return re.sub(pattern, r"\1\n" + block.replace("\\", "\\\\"),
                      dashboard, count=1, flags=re.MULTILINE)
    return dashboard.rstrip() + f"\n\n## {heading}\n\n{block}"


def main():
    dashboard = DASHBOARD.read_text(encoding="utf-8-sig")
    today = date.today().isoformat()

    # --- 1. Merge UPDATE_*.md into Recent Activity, archive to /Done ------
    updates = sorted(UPDATES.glob("UPDATE_*.md"))
    if updates:
        bullets = [f"- {today} (cloud): {first_summary_line(u.read_text(encoding='utf-8-sig'))}"
                   for u in updates]
        dashboard = insert_after_heading(dashboard, "Recent Activity", bullets)
        DONE.mkdir(parents=True, exist_ok=True)
        for u in updates:
            shutil.move(str(u), str(DONE / u.name))
        log(f"[merge-updates] Merged {len(updates)} cloud update(s) into Dashboard")
        audit("merge_updates", "updates_merged", count=len(updates),
              files=[u.name for u in updates])

    # --- 2. Mirror latest HEALTH_*.md status into Alerts (replace old) -----
    health_lines = []
    for h in sorted(UPDATES.glob("HEALTH_*.md")):
        m = re.search(r"^Status:\s*(.+)$", h.read_text(encoding="utf-8-sig"),
                      re.MULTILINE)
        if m:
            health_lines.append(f"- Cloud health ({h.stem.replace('HEALTH_', '')}): {m.group(1).strip()}")
    dashboard = re.sub(r"^- Cloud health \(.*$\n?", "", dashboard,
                       flags=re.MULTILINE)
    if health_lines:
        dashboard = insert_after_heading(dashboard, "Alerts", health_lines)

    dashboard = re.sub(r"^Last Updated: .*$",
                       f"Last Updated: {today}", dashboard,
                       count=1, flags=re.MULTILINE)
    DASHBOARD.write_text(dashboard, encoding="utf-8")
    if not updates and not health_lines:
        log("[merge-updates] No cloud updates to merge")


if __name__ == "__main__":
    main()
