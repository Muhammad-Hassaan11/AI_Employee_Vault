"""Shared helpers for AI Employee watcher scripts.

Loads configuration from the vault-root .env file (KEY=VALUE lines) and
provides common paths + task-file creation used by all watchers.
No third-party dependencies - stdlib only.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.resolve()
NEEDS_ACTION_DIR = VAULT_ROOT / "Needs_Action"
PENDING_APPROVAL_DIR = VAULT_ROOT / "Pending_Approval"
LOGS_DIR = VAULT_ROOT / "Logs"
STATE_DIR = Path(__file__).parent / ".state"


def load_env():
    """Load KEY=VALUE pairs from <vault>/.env into os.environ (no override)."""
    env_file = VAULT_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_state(name: str) -> dict:
    """Load persisted watcher state (e.g. seen message IDs)."""
    path = STATE_DIR / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(name: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / f"{name}.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return slug[:max_len] or "task"


def create_task_file(source: str, title: str, body: str,
                     priority: str = "normal", task_type: str = "message") -> Path:
    """Write a task file into /Needs_Action for Atlas to process."""
    NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{source}_{slugify(title)}.md"
    path = NEEDS_ACTION_DIR / filename
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""---
type: {task_type}
priority: {priority}
status: pending
source: {source}
created_at: {now}
---

# {title}

{body}

## Status History
- {now}: Task created by {source} watcher
"""
    path.write_text(content, encoding="utf-8")
    log(f"[{source}] Created task: {filename}")
    audit(source, "task_created", file=filename, priority=priority,
          task_type=task_type)
    return path


def log(message: str) -> None:
    """Append to today's log file and print."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    log_file = LOGS_DIR / f"{now.strftime('%Y-%m-%d')}.md"
    line = f"- {now.strftime('%H:%M:%S')} {message}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())


def audit(component: str, action: str, status: str = "ok", **details) -> None:
    """Append a structured entry to the machine-readable audit trail.

    Every component (watchers, MCP servers, executors, loops) records what it
    did here so the weekly audit and CEO briefing can reconstruct activity.
    Written as JSON Lines to Logs/audit.jsonl.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "component": component,
        "action": action,
        "status": status,
    }
    if details:
        entry["details"] = details
    with open(LOGS_DIR / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def with_retry(fn, attempts: int = 3, base_delay: float = 2.0,
               component: str = "unknown", action: str = "call"):
    """Run fn() with exponential-backoff retries; audit each failure.

    Returns fn()'s result, or raises the last exception after all attempts
    (callers decide whether to degrade gracefully or surface the error).
    """
    import time as _time
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - deliberate catch-all for retry
            last_exc = e
            audit(component, action, status="retry",
                  attempt=attempt, error=str(e)[:300])
            if attempt < attempts:
                _time.sleep(base_delay * (2 ** (attempt - 1)))
    audit(component, action, status="failed", error=str(last_exc)[:300])
    raise last_exc
