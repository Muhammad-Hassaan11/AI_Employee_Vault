#!/usr/bin/env python3
"""
Health monitor for the always-on Cloud agent (Platinum tier).

Checks the things that silently kill an unattended AI Employee:
    - disk space on the VM
    - task backlog (Needs_Action piling up = reasoning loop broken)
    - approvals waiting on the human (surfaced so nothing rots in queue)
    - watcher liveness (last watcher entry in Logs/audit.jsonl)
    - Odoo reachability (HTTP, via ODOO_URL)

Writes a snapshot to /Updates/HEALTH_<agent>.md (overwritten each run);
the local agent's merge_updates.py mirrors the Status line into
Dashboard.md. Also audits to Logs/audit.jsonl. Degrades gracefully:
a failing check makes the status DEGRADED, never crashes the run.

Usage:  python3 Scripts/health_monitor.py
No third-party dependencies - stdlib only.
"""

import json
import os
import shutil
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Watchers"))
from vault_env import VAULT_ROOT, load_env, log, audit  # noqa: E402

WATCHER_COMPONENTS = {"gmail", "whatsapp", "linkedin", "filesystem"}
WATCHER_STALE_AFTER = timedelta(hours=2)
DISK_MIN_FREE_GB = 2
BACKLOG_WARN = 10


def check_disk() -> tuple:
    usage = shutil.disk_usage(VAULT_ROOT)
    free_gb = usage.free / 1e9
    ok = free_gb >= DISK_MIN_FREE_GB
    return ok, f"Disk: {free_gb:.1f} GB free"


def check_backlog() -> tuple:
    n = len(list((VAULT_ROOT / "Needs_Action").glob("*.md")))
    return n < BACKLOG_WARN, f"Needs_Action backlog: {n} task(s)"


def check_approvals() -> tuple:
    n = len(list((VAULT_ROOT / "Pending_Approval").glob("*.md")))
    return True, f"Pending_Approval: {n} item(s) awaiting human review"


def check_watchers() -> tuple:
    """Any watcher activity in audit.jsonl within the staleness window?"""
    audit_file = VAULT_ROOT / "Logs" / "audit.jsonl"
    if not audit_file.exists():
        return False, "Watchers: no audit trail yet"
    latest = None
    for line in audit_file.read_text(encoding="utf-8").splitlines()[-500:]:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("component") in WATCHER_COMPONENTS:
            latest = entry.get("ts")
    if latest is None:
        return False, "Watchers: no recent watcher entries in audit log"
    age = datetime.now() - datetime.fromisoformat(latest)
    ok = age <= WATCHER_STALE_AFTER
    return ok, f"Watchers: last activity {int(age.total_seconds() // 60)} min ago"


def check_odoo() -> tuple:
    url = os.environ.get("ODOO_URL", "").rstrip("/")
    if not url:
        return True, "Odoo: not configured (skipped)"
    try:
        with urllib.request.urlopen(f"{url}/web/login", timeout=10) as resp:
            code = resp.status
        if code == 200:
            return True, f"Odoo: reachable at {url}"
        return False, f"Odoo: HTTP {code} at {url}"
    except Exception as e:  # noqa: BLE001 - any failure means unreachable
        return False, f"Odoo: unreachable ({str(e)[:80]})"


def main():
    load_env()
    agent = os.environ.get("AGENT_ROLE", "cloud")
    checks = [check_disk, check_backlog, check_approvals,
              check_watchers, check_odoo]
    results = []
    all_ok = True
    for check in checks:
        try:
            ok, detail = check()
        except Exception as e:  # noqa: BLE001 - a broken check must not kill the monitor
            ok, detail = False, f"{check.__name__}: check failed ({str(e)[:80]})"
        results.append((ok, detail))
        all_ok = all_ok and ok

    status = "OK" if all_ok else "DEGRADED"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # ASCII markers: Windows consoles (cp1252) choke on emoji in print().
    lines = "\n".join(f"- {'[OK]' if ok else '[WARN]'} {detail}"
                      for ok, detail in results)
    snapshot = f"""---
type: health_snapshot
agent: {agent}
generated: {now}
---

# Cloud Health - {agent}

Status: {status} ({now})

{lines}
"""
    updates = VAULT_ROOT / "Updates"
    updates.mkdir(parents=True, exist_ok=True)
    (updates / f"HEALTH_{agent}.md").write_text(snapshot, encoding="utf-8")
    log(f"[health-monitor] {agent} status: {status}")
    audit("health_monitor", "snapshot", status="ok" if all_ok else "degraded",
          agent=agent, details={d: o for o, d in results})
    print(snapshot)


if __name__ == "__main__":
    main()
