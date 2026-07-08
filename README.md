# AI_Employee_Vault

An automated AI Employee ("Atlas") powered by Claude Code that monitors an
Obsidian vault, triages incoming work from Gmail / WhatsApp / a LinkedIn
content calendar, plans and executes tasks with Agent Skills, and routes
every sensitive action through a human-in-the-loop approval queue.

## Tier

**Silver — Functional Assistant**

- ✅ Three watcher scripts (Gmail, WhatsApp, LinkedIn) + the original file watcher
- ✅ Automatic LinkedIn business posting pipeline (calendar → draft → approval → publish)
- ✅ Claude reasoning loop that creates `PLAN_*.md` files and executes them
- ✅ MCP server for external action (`vault-email`, sends email via SMTP)
- ✅ Human-in-the-loop approval workflow (`/Pending_Approval` + approval executor)
- ✅ Scheduling via Windows Task Scheduler (`Scripts/register_tasks.ps1`)
- ✅ All AI functionality implemented as Agent Skills in `/Skills/`

## Architecture

```
  Gmail ──▶ gmail_watcher.py ──┐
  WhatsApp ─▶ whatsapp_watcher ─┼──▶ /Needs_Action ──▶ Claude reasoning loop
  LinkedIn calendar ─▶ linkedin_watcher ┘                (run_employee.ps1)
  /Inbox ──▶ file_watcher.py ──┘                              │
                                              ┌───────────────┼────────────┐
                                              ▼               ▼            ▼
                                          /Plans        Agent Skills   /Done + Logs
                                        (PLAN_*.md)          │         + Dashboard
                                                             ▼
                              sensitive actions ──▶ /Pending_Approval (status: pending)
                                                             │  human edits status
                                                             ▼
                                              approval_executor.py (scheduled)
                                              ├─ email  → SMTP / vault-email MCP
                                              └─ post   → LinkedIn API (ugcPosts)
```

## Components

| Path | Purpose |
|------|---------|
| `Watchers/gmail_watcher.py` | Polls Gmail (IMAP) for unread mail → tasks in `/Needs_Action` |
| `Watchers/whatsapp_watcher.py` | Polls Twilio WhatsApp API for inbound messages → tasks |
| `Watchers/linkedin_watcher.py` | Turns due rows in `LinkedIn/Content_Calendar.md` into post-drafting tasks |
| `file_watcher.py` | Original inbox watcher: `/Inbox` → `/Needs_Action` |
| `Scripts/run_employee.ps1` | Reasoning loop: runs watchers, invokes `claude -p` to plan + execute, then the approval executor |
| `Scripts/approval_executor.py` | Executes ONLY human-approved actions; archives rejected ones |
| `Scripts/linkedin_poster.py` | Publishes approved posts via the LinkedIn ugcPosts API |
| `Scripts/register_tasks.ps1` | Registers/unregisters all Task Scheduler jobs |
| `MCP/email_server.py` | Stdio MCP server (`vault-email`) exposing `send_email` + `check_smtp_config` |
| `.mcp.json` | Registers the MCP server with Claude Code |
| `LinkedIn/Content_Calendar.md` | Sales-content schedule driving automatic LinkedIn posting |

## Agent Skills

All AI functionality is skill-driven (`/Skills/*/SKILL.md`, per the
[Agent Skills spec](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)):

| Skill | Purpose |
|-------|---------|
| `process-task` | End-to-end task handling: read → plan → execute → archive |
| `summarize-file` | Extract overview, key points, and action items from files |
| `linkedin-post` | Draft sales-oriented LinkedIn posts → `/Pending_Approval` |
| `send-email` | Draft emails → `/Pending_Approval` → send after approval |
| `handle-approvals` | Report and process the approval queue |

## Human-in-the-Loop Approval Workflow

1. Atlas writes any sensitive action (email, LinkedIn post) to
   `/Pending_Approval/*.md` with `status: pending` in the frontmatter.
2. **You** review the file in Obsidian and change the status to
   `approved` or `rejected`.
3. `Scripts/approval_executor.py` (scheduled every 10 min, or run manually)
   sends/publishes approved items and archives rejected ones to `/Done`.
   Nothing is ever sent without your explicit approval — the MCP server
   refuses `send_email` calls unless `approved=true`, which Atlas may only
   set after your sign-off.

## Setup

### 1. Prerequisites

- Python 3.8+ (stdlib only — no pip installs needed)
- Claude Code CLI
- Obsidian (optional, for reviewing/approving)

### 2. Configure credentials

```powershell
Copy-Item .env.example .env
# then edit .env with your values:
#   GMAIL_ADDRESS / GMAIL_APP_PASSWORD  (Gmail watcher, IMAP)
#   SMTP_USER / SMTP_PASSWORD           (email sending)
#   TWILIO_*                            (WhatsApp watcher)
#   LINKEDIN_ACCESS_TOKEN / LINKEDIN_PERSON_URN  (LinkedIn publishing)
```

Watchers exit gracefully if their credentials aren't set, so you can enable
channels one at a time. `.env` is gitignored.

### 3. Schedule everything (Task Scheduler)

```powershell
powershell -File Scripts\register_tasks.ps1          # register all jobs
powershell -File Scripts\register_tasks.ps1 -Unregister  # remove them
```

Registered jobs: Gmail watcher (15 min), WhatsApp watcher (15 min),
LinkedIn watcher (60 min), approval executor (10 min), reasoning loop (30 min).

### 4. Or run manually

```powershell
powershell -File Scripts\run_employee.ps1   # one full cycle
python Watchers\gmail_watcher.py --loop 300 # or watch continuously
```

## LinkedIn Sales Posting

Add rows to `LinkedIn/Content_Calendar.md`:

```
| 2026-07-09 | Case study: automating email triage with AI | pending |
```

When the date arrives, the LinkedIn watcher creates a drafting task; Atlas
drafts the post with the `linkedin-post` skill into `/Pending_Approval`;
you approve it; the approval executor publishes it via the LinkedIn API.

## Security

- `.env`, `*.secret`, `*.token`, `credentials.json`, and `Watchers/.state/`
  are gitignored — never commit credentials.
- The Gmail watcher connects read-only and never modifies your mailbox.
- Sends/publishes happen only through the approval executor or an
  explicitly approved MCP call. The Company Handbook forbids sending any
  message without human approval.

## License

Personal use - Muhammad Hassaan

<!-- graph-links -->
## Related

- [[CLAUDE]] · [[Dashboard]] · [[Company_Handbook]] · [[Skills_Index]]
