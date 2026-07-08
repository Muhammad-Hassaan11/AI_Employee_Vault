---
description: Start a Ralph Wiggum persistence loop - keep working until the task is complete
argument-hint: "<task prompt>" [--completion-promise PHRASE] [--max-iterations N]
---

Start a Ralph Wiggum loop for: $ARGUMENTS

Do the following:

1. Parse the arguments: the quoted task prompt, an optional
   `--completion-promise PHRASE` (default `TASK_COMPLETE`), and an optional
   `--max-iterations N` (default 10).
2. Write `Scripts/.ralph/state.json` (create the folder if needed) with:
   ```json
   {
     "active": true,
     "prompt": "<the task prompt>",
     "completion_promise": "<PHRASE>",
     "max_iterations": <N>,
     "iteration": 0,
     "started_at": "<ISO timestamp>"
   }
   ```
3. Begin working on the task prompt immediately, following CLAUDE.md and the
   vault skills as usual.
4. The Stop hook (Scripts/ralph_stop_hook.py) will now block every attempt to
   stop and re-inject the prompt until your reply ends with the exact
   completion promise phrase - so only output that phrase when the task is
   genuinely, verifiably complete (e.g. the task files really are in /Done).
