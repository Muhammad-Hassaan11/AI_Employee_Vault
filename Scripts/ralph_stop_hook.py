#!/usr/bin/env python3
"""
Ralph Wiggum Stop hook for AI Employee Vault.

Registered in .claude/settings.json as a Stop hook. When a Ralph loop is
active (state file written by /ralph-loop or Scripts/ralph_loop.ps1), this
hook intercepts Claude's attempt to exit:

    - completion promise found in Claude's last output -> allow exit
    - max iterations reached                           -> allow exit (give up)
    - otherwise -> block the stop and re-inject the prompt, so Claude sees
      its own previous (incomplete) output and keeps working

State file: Scripts/.ralph/state.json
    {"active": true, "prompt": "...", "completion_promise": "TASK_COMPLETE",
     "max_iterations": 10, "iteration": 0, "started_at": "..."}

The hook communicates by printing JSON: {"decision": "block", "reason": ...}
blocks the stop; exiting 0 with no output allows it.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent.resolve()
STATE_FILE = VAULT_ROOT / "Scripts" / ".ralph" / "state.json"


def audit(action: str, status: str = "ok", **details):
    logs = VAULT_ROOT / "Logs"
    logs.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "component": "ralph-loop", "action": action, "status": status}
    if details:
        entry["details"] = details
    with open(logs / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_assistant_text(transcript_path: str) -> str:
    """Concatenate text of the final assistant message in the transcript."""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    text = ""
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = entry.get("message", {})
        if entry.get("type") == "assistant" or msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                parts = [c.get("text", "") for c in content
                         if isinstance(c, dict) and c.get("type") == "text"]
                if parts:
                    text = "\n".join(parts)
            elif isinstance(content, str) and content:
                text = content
    return text


def finish(state: dict, reason: str):
    state["active"] = False
    state["finished_at"] = datetime.now().isoformat(timespec="seconds")
    state["finish_reason"] = reason
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    audit("loop_finished", reason=reason, iterations=state.get("iteration", 0))
    sys.exit(0)  # allow the stop


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    if not STATE_FILE.exists():
        sys.exit(0)
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        sys.exit(0)
    if not state.get("active"):
        sys.exit(0)

    output = last_assistant_text(hook_input.get("transcript_path", ""))
    promise = state.get("completion_promise", "TASK_COMPLETE")
    if promise and promise in output:
        finish(state, f"completion promise '{promise}' found")

    iteration = int(state.get("iteration", 0)) + 1
    max_iter = int(state.get("max_iterations", 10))
    if iteration > max_iter:
        finish(state, f"max iterations ({max_iter}) reached without completion")

    state["iteration"] = iteration
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    audit("loop_iteration", iteration=iteration, max_iterations=max_iter)

    reason = (
        f"[Ralph loop iteration {iteration}/{max_iter}] The task is not "
        f"complete yet. Review your previous output above, fix whatever is "
        f"unfinished or failing, and continue.\n\nOriginal task:\n"
        f"{state.get('prompt', '(no prompt recorded)')}\n\n"
        f"When the task is fully complete, end your reply with the exact "
        f"phrase: {promise}"
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
