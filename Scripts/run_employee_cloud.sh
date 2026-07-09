#!/usr/bin/env bash
# Cloud Reasoning Loop (Platinum tier) - runs on the always-on Oracle VM.
# ----------------------------------------------------------------------
# The CLOUD agent's work zone: email triage + draft replies + social post
# drafts. Everything is DRAFT-ONLY - drafts land in /Pending_Approval with
# status: pending; the LOCAL agent (your PC) holds the approvals, the
# WhatsApp session, banking, and the final send/post.
#
# Cycle:  sync pull -> watchers -> claim-by-move -> Claude (draft-only)
#         -> health snapshot -> sync push
#
# Run manually:   bash Scripts/run_employee_cloud.sh
# Scheduled by:   Cloud/systemd/ai-employee.timer (every 30 min)
set -uo pipefail

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$VAULT_ROOT"
export AGENT_ROLE=cloud

log() {
    local line="- $(date +%H:%M:%S) [cloud-loop] $1"
    echo "$line"
    mkdir -p Logs
    echo "$line" >> "Logs/$(date +%F).md"
}

log "Cloud run started"

# --- Step 1: Pull the latest vault state (approvals, new calendar rows) ----
bash "$VAULT_ROOT/Scripts/vault_sync.sh" pull

# --- Step 2: Run the cloud-owned watchers once ------------------------------
# (WhatsApp is LOCAL-only: its session never exists on the cloud.)
python3 "$VAULT_ROOT/Watchers/gmail_watcher.py"
python3 "$VAULT_ROOT/Watchers/linkedin_watcher.py"
python3 "$VAULT_ROOT/Watchers/filesystem_watcher.py"

# --- Step 3: Claim tasks in the cloud work zone (claim-by-move) --------------
python3 "$VAULT_ROOT/Scripts/claim_task.py" claim-eligible --agent cloud
# Push claims immediately so Local never double-works these tasks.
bash "$VAULT_ROOT/Scripts/vault_sync.sh" push

# --- Step 4: If we claimed work, run Claude in draft-only cloud mode ---------
CLAIMED=$(find "$VAULT_ROOT/In_Progress/cloud" -maxdepth 1 -name '*.md' | wc -l)
if [[ "$CLAIMED" -gt 0 ]]; then
    log "Processing $CLAIMED claimed task(s) with Claude"
    claude -p 'You are Atlas, the AI Employee, running as the CLOUD agent. Use the cloud-triage skill in /Skills/cloud-triage and follow CLAUDE.md Platinum rules:
1. Process ONLY files in /In_Progress/cloud - never touch /In_Progress/local.
2. For each task: create /Plans/PLAN_[taskname].md, then DRAFT the response (email reply, LinkedIn/social post) into /Pending_Approval with status: pending and drafted_by: cloud. NEVER send or publish anything.
3. You must NOT edit Dashboard.md (single-writer rule: Local owns it). Instead write a short note to /Updates/UPDATE_[timestamp]_[slug].md describing what you drafted.
4. Move finished task files and plans to /Done and log to /Logs.
5. WhatsApp, payments, and banking are outside your work zone - if a task needs them, move it back to /Needs_Action for the Local agent and note why.' \
        --permission-mode acceptEdits
    log "Claude cloud reasoning finished"
else
    log "No tasks in cloud work zone"
fi

# --- Step 5: Health snapshot -> /Updates/HEALTH_cloud.md ---------------------
python3 "$VAULT_ROOT/Scripts/health_monitor.py"

# --- Step 6: Push drafts, updates, and logs back to the shared vault ---------
bash "$VAULT_ROOT/Scripts/vault_sync.sh" push

log "Cloud run complete"
