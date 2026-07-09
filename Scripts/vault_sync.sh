#!/usr/bin/env bash
# Vault sync (Cloud/Linux side) - Platinum "Delegation via Synced Vault".
#
# The two agents (Cloud VM + Local PC) communicate ONLY by writing files
# into the shared git repository. This script pulls the other agent's
# changes and pushes ours. Secrets never sync: .env, tokens, credentials
# and session files are all covered by .gitignore, so the cloud never
# receives WhatsApp sessions or banking credentials.
#
# Usage:  bash Scripts/vault_sync.sh pull   # before working
#         bash Scripts/vault_sync.sh push   # after working
#         bash Scripts/vault_sync.sh        # full cycle (pull + push)
set -uo pipefail

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$VAULT_ROOT"
AGENT="${AGENT_ROLE:-cloud}"
MODE="${1:-full}"

log() {
    local line="- $(date +%H:%M:%S) [vault-sync/$AGENT] $1"
    echo "$line"
    mkdir -p Logs
    echo "$line" >> "Logs/$(date +%F).md"
}

if ! git remote get-url origin >/dev/null 2>&1; then
    log "No git remote 'origin' configured - skipping sync (single-machine mode)"
    exit 0
fi

if [[ "$MODE" == "pull" || "$MODE" == "full" ]]; then
    if git pull --rebase --autostash origin "$(git rev-parse --abbrev-ref HEAD)"; then
        log "Pulled latest vault state"
    else
        git rebase --abort 2>/dev/null
        log "WARNING: pull failed (conflict or network) - continuing with local state"
    fi
fi

if [[ "$MODE" == "push" || "$MODE" == "full" ]]; then
    git add -A
    if git diff --cached --quiet; then
        log "Nothing to push"
    else
        git commit -m "sync($AGENT): vault state $(date '+%F %H:%M')" --quiet
        if git push origin "$(git rev-parse --abbrev-ref HEAD)"; then
            log "Pushed vault changes"
        else
            # Someone pushed in between: rebase once and retry.
            git pull --rebase --autostash origin "$(git rev-parse --abbrev-ref HEAD)" \
                && git push origin "$(git rev-parse --abbrev-ref HEAD)" \
                && log "Pushed vault changes (after rebase)" \
                || log "WARNING: push failed - changes remain committed locally"
        fi
    fi
fi
