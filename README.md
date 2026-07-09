# AI_Employee_Vault

An autonomous AI Employee ("Atlas") powered by Claude Code that manages
personal and business affairs 24/7 from an Obsidian vault: it triages
Gmail / WhatsApp / a LinkedIn content calendar, keeps books in a
self-hosted Odoo, posts to Facebook / Instagram / X, writes a weekly CEO
briefing — and routes **every** sensitive action through a
human-in-the-loop approval queue.

> New here? **[START_AI_EMPLOYEE.md](START_AI_EMPLOYEE.md)** is the
> operator guide: exactly which commands to run, in what order, on your
> PC and on the Oracle Cloud VM.

## Tier

**Platinum — Always-On Cloud + Local Executive**

Everything from Bronze → Gold, plus:

- ✅ Always-on **Cloud agent** on an Oracle VM (systemd watchdog + 30-min reasoning timer + health monitoring)
- ✅ **Work-zone specialization** — Cloud: email triage, draft replies, social drafts (draft-only). Local: approvals, WhatsApp, payments, final send/post
- ✅ **Delegation via synced vault** (git): claim-by-move via `/In_Progress/<agent>/`, single-writer `Dashboard.md` (Local), Cloud reports through `/Updates/`
- ✅ **Secrets never sync** — `.env`, tokens, sessions are gitignored; the Cloud VM never holds WhatsApp sessions, SMTP send, or banking credentials
- ✅ **Odoo Community 19 on the Cloud VM** with automatic HTTPS (Caddy/Let's Encrypt), nightly `pg_dumpall` backups (7-day retention), container healthchecks — draft-only writes via MCP, Local approval to post
- ✅ Passes the **Platinum demo gate**: email arrives while Local is offline → Cloud drafts reply + approval file → you approve on return → Local sends via MCP → logs → `/Done`

Gold-tier foundation: 3 MCP servers (email / Odoo / social), weekly
audit → CEO briefing, Ralph Wiggum persistence loop, cross-domain
(personal + business) routing, error recovery with retries, structured
audit logging (`Logs/audit.jsonl`).

## Architecture

```
            ┌──────────────── ORACLE CLOUD VM (24/7, AGENT_ROLE=cloud) ─────────────────┐
            │ systemd: ai-watchdog.service  → watchdog.py (gmail/linkedin/fs watchers)   │
            │          ai-employee.timer    → run_employee_cloud.sh every 30 min         │
            │                                                                            │
            │ sync pull → watchers → claim-by-move → Claude (cloud-triage, DRAFT-ONLY)   │
            │      → drafts to /Pending_Approval + notes to /Updates → health → push     │
            │                                                                            │
            │ Odoo 19 + Postgres + Caddy HTTPS + nightly backups (docker-compose.cloud)  │
            └──────────────────────────────┬─────────────────────────────────────────────┘
                                           │  git-synced vault (markdown/state only,
                                           │  secrets NEVER sync)
            ┌──────────────────────────────┴─────────────────────────────────────────────┐
            │                    LOCAL PC (AGENT_ROLE=local)                              │
            │ Task Scheduler → run_employee.ps1:                                          │
            │   sync pull → all watchers (incl. WhatsApp) → claim → Claude reasoning      │
            │   → approval_executor (ONLY thing that sends/posts) → merge_updates         │
            │   → Dashboard.md (single writer) → sync push                                │
            │                                                                             │
            │ HUMAN: reviews /Pending_Approval in Obsidian, flips status → approved       │
            └─────────────────────────────────────────────────────────────────────────────┘
```

Task lifecycle: `/Needs_Action` → claim-by-move → `/In_Progress/<agent>/`
→ plan in `/Plans` → sensitive actions to `/Pending_Approval`
(`status: pending`) → human approval → `approval_executor.py` executes →
`/Done` + `Logs/` + `Dashboard.md`.

## Components

### Perception (Watchers)

| Path | Purpose |
|------|---------|
| `Watchers/gmail_watcher.py` | Polls Gmail (IMAP, read-only) → tasks in `/Needs_Action` |
| `Watchers/whatsapp_watcher.py` | Twilio WhatsApp inbound → tasks (**Local-only**) |
| `Watchers/linkedin_watcher.py` | Due rows in `LinkedIn/Content_Calendar.md` → drafting tasks |
| `Watchers/filesystem_watcher.py` / `file_watcher.py` | `/Inbox` drops → tasks |
| `Scripts/watchdog.py` | Supervises watchers with exponential-backoff restarts |

### Reasoning (Claude Code)

| Path | Purpose |
|------|---------|
| `Scripts/run_employee.ps1` | **Local** loop: sync → watchers → claim → Claude → approval executor → merge updates → sync |
| `Scripts/run_employee_cloud.sh` | **Cloud** loop: sync → watchers → claim → Claude (draft-only) → health → sync |
| `Scripts/ralph_loop.ps1` + `Scripts/ralph_stop_hook.py` | Ralph Wiggum persistence: Stop hook re-injects the prompt until the task is verifiably done |
| `CLAUDE.md` | Atlas's master instructions (incl. Platinum two-agent rules) |

### Action (MCP servers — one per action type)

| Server | Path | Tools |
|--------|------|-------|
| `vault-email` | `MCP/email_server.py` | `send_email` (approval-gated), `check_smtp_config` |
| `vault-odoo` | `MCP/odoo_server.py` | invoices, expenses, customers, `accounting_summary` — writes are **DRAFT-only** (Odoo JSON-RPC) |
| `vault-social` | `MCP/social_server.py` | Facebook / Instagram / X posting (approval-gated) + engagement summaries |

### Platinum two-agent machinery

| Path | Purpose |
|------|---------|
| `Scripts/claim_task.py` | Claim-by-move: `/Needs_Action` → `/In_Progress/<agent>/`, enforcing work zones |
| `Scripts/vault_sync.sh` / `.ps1` | Git vault sync (pull --rebase / commit / push), no-op without a remote |
| `Scripts/merge_updates.py` | Local-only: merges Cloud's `/Updates/UPDATE_*.md` into `Dashboard.md`, mirrors `HEALTH_*` status into Alerts |
| `Scripts/health_monitor.py` | Cloud health snapshot (disk, backlog, watcher liveness, Odoo reachability) → `/Updates/HEALTH_cloud.md` |
| `Cloud/setup_oracle_vm.sh` | One-shot Oracle VM bootstrap (packages, clone, firewall, systemd, Odoo) |
| `Cloud/systemd/*` | `ai-watchdog.service`, `ai-employee.service` + `.timer` |
| `Odoo/docker-compose.cloud.yml` + `Odoo/Caddyfile` | Cloud Odoo with HTTPS, healthchecks, nightly backups |

### Human-in-the-loop

| Path | Purpose |
|------|---------|
| `Scripts/approval_executor.py` | The **only** component that executes approved actions; archives rejections |
| `Pending_Approval/` | Action files with `status: pending` frontmatter — you flip to `approved`/`rejected` in Obsidian |

### Business intelligence

| Path | Purpose |
|------|---------|
| `Scripts/weekly_audit.ps1` + `Skills/weekly-audit/` | Weekly audit → `/Briefings/CEO_Briefing_[date].md` (revenue, bottlenecks, suggestions) |
| `Logs/audit.jsonl` | Structured audit trail of every action (who/what/when/status) |

## Agent Skills

All AI functionality is skill-driven (`/Skills/*/SKILL.md`):

| Skill | Purpose |
|-------|---------|
| `process-task` | End-to-end task handling: read → plan → execute → archive |
| `summarize-file` | Overview, key points, action items from files |
| `linkedin-post` | Sales-oriented LinkedIn drafts → approval queue |
| `send-email` | Email drafts → approval queue → send after approval |
| `social-post` | Facebook / Instagram / X drafts + engagement summaries |
| `handle-approvals` | Report and process the approval queue |
| `weekly-audit` | Odoo + social + audit-log data → CEO briefing |
| `cloud-triage` | **Platinum**: Cloud agent's draft-only work zone playbook |

## Work zones & delegation rules (Platinum)

| | Cloud agent (VM) | Local agent (PC) |
|---|---|---|
| Owns | Email triage, draft replies, social/LinkedIn drafts, Odoo draft entries | Approvals, WhatsApp session, payments/banking, **final send/post**, Dashboard.md |
| Claims sources | `gmail`, `linkedin`, `calendar`, `file` | anything |
| May send/publish? | **Never** | Only via `approval_executor.py` after human approval |
| Reports via | `/Updates/UPDATE_*.md` + `HEALTH_cloud.md` | `Dashboard.md` (single writer) |

- **Claim-by-move**: first agent to move a task from `/Needs_Action` to
  `/In_Progress/<agent>/` owns it; the move is pushed immediately so the
  other agent ignores it.
- **Secrets never sync**: `.gitignore` excludes `.env`, `*.token`,
  `*.secret`, `*.session`, `*.pem`, `*.key`, credentials, watcher state,
  and Odoo backups. Each machine keeps its own `.env`.

## Setup (Local)

```powershell
# 1. Credentials
Copy-Item .env.example .env    # then fill in your values (AGENT_ROLE=local)

# 2. Schedule everything (watchers, reasoning loop, approvals, weekly audit)
powershell -File Scripts\register_tasks.ps1

# 3. Or run one full cycle manually
powershell -File Scripts\run_employee.ps1
```

## Setup (Cloud — Oracle VM)

```bash
export VAULT_REPO="https://github.com/<you>/AI_Employee_Vault.git"
git clone "$VAULT_REPO" ~/AI_Employee_Vault
cd ~/AI_Employee_Vault
bash Cloud/setup_oracle_vm.sh     # packages, firewall, systemd, Odoo
nano .env                          # cloud-zone credentials ONLY
claude login                       # authenticate Claude Code once
bash Scripts/run_employee_cloud.sh # verify one cycle end-to-end
```

Full click-by-click instructions (creating the VM, SSH, DNS for Odoo,
troubleshooting): **[START_AI_EMPLOYEE.md](START_AI_EMPLOYEE.md)**.

## The Platinum demo gate (works out of the box)

1. An email arrives while your PC is off.
2. Cloud: Gmail watcher files a task → cloud loop claims it →
   Claude drafts a reply into `/Pending_Approval/EMAIL_*.md`
   (`status: pending`, `drafted_by: cloud`) → pushes the vault.
3. You come back, your local loop pulls; you open the draft in Obsidian
   and set `status: approved`.
4. `approval_executor.py` sends it via SMTP/`vault-email` MCP, logs to
   `Logs/audit.jsonl`, archives everything to `/Done`, and
   `merge_updates.py` posts the activity to `Dashboard.md`.

## Security

- **Credential isolation per machine** — `.env` is gitignored; the Cloud
  VM never stores WhatsApp sessions, SMTP send, or banking credentials.
- **Draft-only cloud** — the cloud prompt, skill, and handbook all forbid
  sending; only the local approval executor performs sends/posts, and the
  `vault-email` MCP refuses `send_email` without `approved=true`.
- **Odoo hardening** — no public 8069; Caddy terminates HTTPS; Postgres
  password from `.env`; nightly backups with 7-day retention.
- **Audit everything** — human-readable `Logs/[date].md` plus structured
  `Logs/audit.jsonl`; the weekly audit reads both.
- **Graceful degradation** — retries with exponential backoff
  (`vault_env.with_retry`), watchers exit cleanly when unconfigured,
  health monitor reports DEGRADED instead of crashing.

## Documentation & lessons learned

- Architecture blueprint: this README + `CLAUDE.md` (agent rules) +
  `Company_Handbook.md` (rules of engagement)
- Operator guide: `START_AI_EMPLOYEE.md`
- Key lesson: file-over-app wins — every hand-off (watcher → reasoner →
  approval → executor → dashboard) is a markdown file move, which makes
  the whole system observable in Obsidian and trivially auditable in git
  history.

## License

Personal use - Muhammad Hassaan

<!-- graph-links -->
## Related

- [[CLAUDE]] · [[Dashboard]] · [[Company_Handbook]] · [[Skills_Index]] · [[START_AI_EMPLOYEE]]
