#!/usr/bin/env python3
"""
Watchdog / Process Manager for AI Employee Vault.

Supervises the long-running watchers (Gmail, WhatsApp, LinkedIn, filesystem)
in --loop mode and restarts any that crash, so the AI Employee's "senses"
stay alive without a human babysitting them. This is the stepping stone to
Platinum's always-on operation.

Improved over the reference watchdog in the hackathon guide:
    - cross-platform (Windows/macOS/Linux), stdlib only
    - supervises live child processes via subprocess.poll() instead of
      guessing from PID files
    - exponential backoff per process so a hard-failing watcher (e.g. bad
      credentials) doesn't spin-restart forever
    - every start / crash / restart is written to Logs/audit.jsonl
    - clean shutdown on Ctrl+C: children are terminated, not orphaned

For production always-on hosting, wrap THIS script in PM2 / systemd / a
Task Scheduler "at startup" trigger so it too is resurrected on reboot.

Usage:
    python Scripts/watchdog.py
    python Scripts/watchdog.py --only gmail linkedin   # subset
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Watchers"))
from vault_env import VAULT_ROOT, load_env, log, audit  # noqa: E402

PY = sys.executable or "python"

# name -> command (each watcher supervised in --loop mode)
PROCESSES = {
    "gmail":      [PY, str(VAULT_ROOT / "Watchers" / "gmail_watcher.py"), "--loop", "300"],
    "whatsapp":   [PY, str(VAULT_ROOT / "Watchers" / "whatsapp_watcher.py"), "--loop", "300"],
    "linkedin":   [PY, str(VAULT_ROOT / "Watchers" / "linkedin_watcher.py"), "--loop", "3600"],
    "filesystem": [PY, str(VAULT_ROOT / "Watchers" / "filesystem_watcher.py"), "--loop", "60"],
}

CHECK_INTERVAL = 15          # seconds between health checks
MIN_BACKOFF = 5              # seconds
MAX_BACKOFF = 300            # cap restart backoff at 5 min
BACKOFF_RESET_AFTER = 120    # a process alive this long resets its backoff


class Supervised:
    def __init__(self, name: str, cmd: list):
        self.name = name
        self.cmd = cmd
        self.proc = None
        self.backoff = MIN_BACKOFF
        self.next_start = 0.0
        self.started_at = 0.0

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self) -> None:
        try:
            self.proc = subprocess.Popen(
                self.cmd, cwd=str(VAULT_ROOT),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self.started_at = time.time()
            log(f"[watchdog] Started {self.name} (pid {self.proc.pid})")
            audit("watchdog", "process_started", name=self.name, pid=self.proc.pid)
        except Exception as e:
            log(f"[watchdog] Failed to start {self.name}: {e}")
            audit("watchdog", "process_start", status="failed",
                  name=self.name, error=str(e)[:200])

    def note_exit(self) -> None:
        code = self.proc.poll() if self.proc else None
        ran_for = time.time() - self.started_at
        if ran_for >= BACKOFF_RESET_AFTER:
            self.backoff = MIN_BACKOFF  # it was healthy; treat as a fresh crash
        log(f"[watchdog] {self.name} exited (code {code}) after "
            f"{int(ran_for)}s; restarting in {self.backoff}s")
        audit("watchdog", "process_exited", status="failed",
              name=self.name, exit_code=code, ran_seconds=int(ran_for),
              retry_in=self.backoff)
        self.next_start = time.time() + self.backoff
        self.backoff = min(self.backoff * 2, MAX_BACKOFF)
        self.proc = None

    def stop(self) -> None:
        if not self.alive():
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        audit("watchdog", "process_stopped", name=self.name)


def main():
    load_env()
    names = PROCESSES.keys()
    if "--only" in sys.argv:
        names = sys.argv[sys.argv.index("--only") + 1:]
    supervised = [Supervised(n, PROCESSES[n]) for n in names if n in PROCESSES]
    if not supervised:
        print(f"[watchdog] No known processes to supervise. Choices: {list(PROCESSES)}")
        return

    log(f"[watchdog] Supervising: {', '.join(s.name for s in supervised)}")
    audit("watchdog", "started", processes=[s.name for s in supervised])
    for s in supervised:
        s.start()

    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            now = time.time()
            for s in supervised:
                if s.alive():
                    continue
                if s.proc is not None:
                    s.note_exit()
                if now >= s.next_start:
                    s.start()
    except KeyboardInterrupt:
        print("\n[watchdog] Shutting down; stopping children…")
        for s in supervised:
            s.stop()
        audit("watchdog", "stopped")
        log("[watchdog] Stopped.")


if __name__ == "__main__":
    main()
