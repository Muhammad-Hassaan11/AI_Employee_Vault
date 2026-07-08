#!/usr/bin/env python3
"""
File System Watcher for AI Employee Vault.

Watches the /Inbox drop folder for files a human drags in and creates a
task in /Needs_Action for each new one, so Atlas can process it (summarize
a document, extract a to-do, file a receipt, etc.).

Improved over the reference DropFolderHandler in the hackathon guide:
    - stdlib only (no third-party `watchdog` dependency)
    - shares vault_env helpers (task creation, logging, audit trail)
    - de-dupes via persisted state so a file is only tasked once
    - waits for a file to finish copying (size must be stable) before
      tasking it, avoiding half-written uploads
    - the original file is never moved or deleted (handbook: never delete);
      it is linked from the task by absolute path

Run once (for Task Scheduler):
    python Watchers/filesystem_watcher.py
Loop mode:
    python Watchers/filesystem_watcher.py --loop [interval_seconds]
"""

import sys
import time

from vault_env import (
    VAULT_ROOT, load_env, load_state, save_state, create_task_file, log,
)

STATE_NAME = "filesystem_seen"
INBOX_DIR = VAULT_ROOT / "Inbox"
# Ignore Obsidian/OS bookkeeping and files still being written
IGNORE_SUFFIXES = (".tmp", ".part", ".crdownload", ".partial")
IGNORE_NAMES = {".gitkeep", ".ds_store", "thumbs.db"}
TEXT_SUFFIXES = {".md", ".txt", ".csv", ".log", ".json"}
PREVIEW_CHARS = 1500


def _key(path) -> str:
    """Identity for de-dup: name + size + mtime (re-drop of a changed file re-tasks)."""
    st = path.stat()
    return f"{path.name}:{st.st_size}:{int(st.st_mtime)}"


def _is_stable(path, settle: float = 1.0) -> bool:
    """True if the file size is unchanged across a short interval (copy finished)."""
    try:
        first = path.stat().st_size
        time.sleep(settle)
        return path.stat().st_size == first
    except OSError:
        return False


def _preview(path) -> str:
    if path.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            clipped = text[:PREVIEW_CHARS]
            if len(text) > PREVIEW_CHARS:
                clipped += "\n… (truncated)"
            return f"## File Preview\n\n```\n{clipped}\n```\n"
        except OSError:
            pass
    return "(binary or unreadable file — open it directly to review)"


def check_inbox() -> int:
    if not INBOX_DIR.exists():
        log(f"[filesystem] Skipped: {INBOX_DIR} not found")
        return 0

    state = load_state(STATE_NAME)
    seen = set(state.get("seen_keys", []))
    created = 0

    for path in sorted(INBOX_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.name.lower() in IGNORE_NAMES or path.suffix.lower() in IGNORE_SUFFIXES:
            continue
        try:
            key = _key(path)
        except OSError:
            continue
        if key in seen:
            continue
        if not _is_stable(path):
            continue  # still copying — pick it up next pass

        st = path.stat()
        create_task_file(
            source="filesystem",
            title=f"Inbox file: {path.name}",
            body=(
                f"**File:** {path.name}\n"
                f"**Path:** {path.resolve()}\n"
                f"**Size:** {st.st_size:,} bytes\n\n"
                f"{_preview(path)}\n\n"
                f"## Suggested Actions\n"
                f"- [ ] Review the file and decide what it needs\n"
                f"- [ ] Use the `summarize-file` skill if it's a document\n"
                f"- [ ] Route any sensitive follow-up through /Pending_Approval\n"
            ),
            priority="normal",
            task_type="file_drop",
        )
        seen.add(key)
        created += 1

    state["seen_keys"] = list(seen)[-1000:]
    save_state(STATE_NAME, state)
    if created:
        log(f"[filesystem] Created {created} task(s) from /Inbox")
    else:
        print("[filesystem] No new files in /Inbox.")
    return created


def main():
    load_env()
    if "--loop" in sys.argv:
        idx = sys.argv.index("--loop")
        interval = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 60
        print(f"[filesystem] Watching /Inbox every {interval}s. Ctrl+C to stop.")
        while True:
            try:
                check_inbox()
            except Exception as e:
                log(f"[filesystem] ERROR: {e}")
            time.sleep(interval)
    else:
        try:
            check_inbox()
        except Exception as e:
            log(f"[filesystem] ERROR: {e}")
            sys.exit(0)


if __name__ == "__main__":
    main()
