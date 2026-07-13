# AI Employee Dashboard

Last Updated: 2026-07-13

## Quick Status

- Pending Tasks: 0
- In Progress: 0
- Completed Today: 9
- Needs My Approval: 48

## Awaiting Approval

- **7-day IG/FB content calendar (2026-07-12 → 2026-07-18)**: 42 drafts (21 topics x Instagram + Facebook) on AI agents/automation, in `/Pending_Approval` as `INSTAGRAM_*` / `FACEBOOK_*`. Overview + image briefs: [[Social_Content_Calendar]]. Each `instagram_post` file needs a real `image_url` filled in (built from its Image Brief) before you flip `status` to `approved` — no image-generation tool is available to Atlas, so only text drafts + design briefs were produced.
- [FACEBOOK_python_language](Pending_Approval/FACEBOOK_python_language.md) — APPROVED but publish FAILED (Meta access token expired). Refresh the Meta token in `.env`, then re-run the approval executor.
- [INSTAGRAM_python_language](Pending_Approval/INSTAGRAM_python_language.md) — APPROVED but publish FAILED (Meta access token expired). Refresh the Meta token in `.env`, then re-run the approval executor.
- [LINKEDIN_ai_employee](Pending_Approval/LINKEDIN_ai_employee.md) — LinkedIn post draft "AI Employee — what it is and why small businesses are hiring one" (scheduled 2026-07-11 11:55). Flip `status: pending` to `approved`/`rejected`.
- [LINKEDIN_ai_employee_10_hours](Pending_Approval/LINKEDIN_ai_employee_10_hours.md) — LinkedIn post draft. Edit `status: pending` to `approved` (or `rejected`) in the frontmatter, then the approval executor handles the rest.
- [LINKEDIN_3_signs_workflow_automation](Pending_Approval/LINKEDIN_3_signs_workflow_automation.md) — LinkedIn post draft "3 signs your business is ready for workflow automation" (scheduled 2026-07-11). Flip `status: pending` to `approved`/`rejected`.
- [LINKEDIN_case_study_email_triage](Pending_Approval/LINKEDIN_case_study_email_triage.md) — LinkedIn post draft "Case study: automating email triage and follow-ups with AI" (scheduled 2026-07-09). Flip `status: pending` to `approved`/`rejected`.

## Recent Activity

- 2026-07-13 (local): Triaged 9 gmail tasks from /In_Progress/local — 2 Google security notifications (password changed + account recovered for muhammadhassaan.h1@gmail.com; flagged in Alerts for owner verification) and 7 routine promo/notification emails (Twilio ×2, onic/SurveyMonkey survey, foodpanda promo, Duolingo reminder, Apollo support-change notice, Reddit digest). No replies needed (all no-reply senders); nothing sent; all closed to /Done (process-task skill)
- 2026-07-11 (local): Triaged 3 gmail tasks claimed into /In_Progress/local — Instagram recovery-code notification, Skool weekly digest, Alison Courses marketing email — all informational, no reply/action needed, closed to /Done (process-task skill)
- 2026-07-11: Built 7-day Instagram + Facebook content calendar (2026-07-12 to 2026-07-18, 3 posts/day on AI agents/automation) → 42 drafts in /Pending_Approval + [[Social_Content_Calendar]] overview with per-post image briefs (1:1 / 4:5 / 1.91:1 rotation); image files themselves were not generated (no image tool available) (social-post skill)
- 2026-07-11: Drafted Facebook + Instagram posts on the Python language → /Pending_Approval (social-post skill)
- 2026-07-11: Drafted LinkedIn post "AI Employee — what it is and why small businesses are hiring one" (scheduled 11:55) → /Pending_Approval; added row to Content_Calendar (linkedin-post skill)
- 2026-07-11: Drafted LinkedIn post "3 signs your business is ready for workflow automation" → /Pending_Approval (linkedin-post skill)
- 2026-07-11: Drafted LinkedIn post "Case study: automating email triage and follow-ups with AI" → /Pending_Approval (linkedin-post skill)
- 2026-07-11: Triaged WhatsApp from +923222547472 — Twilio sandbox join phrase ("join zulu-problem"), no reply needed; sender now connected to the sandbox

- 2026-07-08: Platinum Tier build complete — two-agent cloud/local split (claim-by-move via /In_Progress, single-writer Dashboard, /Updates merge), git vault sync with secrets isolation, draft-only cloud reasoning loop + cloud-triage skill, Oracle VM bootstrap + systemd (watchdog, 30-min timer), cloud health monitoring, Odoo cloud stack (Caddy HTTPS + nightly backups), rewritten README + new START_AI_EMPLOYEE.md operator guide
- 2026-07-08 (cloud): Platinum two-agent machinery installed: claim-by-move, vault sync, draft-only cloud loop, Oracle VM deployment, Odoo HTTPS stack — merged from /Updates as the pipeline's first live test
- 2026-07-07: Gold Tier build complete — Odoo accounting MCP (vault-odoo, JSON-RPC), social MCP (vault-social: Facebook/Instagram/X posting + summaries), 3 MCP servers registered, weekly audit → CEO briefing pipeline (/Briefings), Ralph Wiggum persistence loop (Stop hook + /ralph-loop + orchestrator), cross-domain routing rules, approval executor extended to facebook_post/instagram_post/tweet
- 2026-07-07: Silver Tier build complete — Gmail/WhatsApp/LinkedIn watchers, email MCP server, approval executor, reasoning loop, Task Scheduler registration, 3 new skills
- 2026-07-07: Drafted LinkedIn post "How an AI Employee saves a small business 10+ hours a week" → /Pending_Approval
- 2026-07-07: Verified approval workflow (rejected test item archived correctly, pending items untouched)
- 2026-02-28: Completed hello world.txt - Personal intro (Muhammad Hassaan, CS student, age 18)
- 2026-02-28: Completed DockerNotes.pdf - Document processed (image-based PDF, requires visual review)
- 2026-02-28: Completed SQL (notes) (1).pdf - Document processed (image-based PDF, requires visual review)
- 2026-02-28: Completed TEST_001 - Summarized Q1 revenue statement ($10,000)

## Alerts

- **Google account security check (owner action)**: Google reports the password for muhammadhassaan.h1@gmail.com was CHANGED and the account was RECOVERED on 2026-07-12 ~08:55 GMT (recovery email muhammadhass745@gmail.com). If this was you, no action needed. If not, secure the account immediately — go directly to https://myaccount.google.com/notifications (type the URL yourself; don't click email links) and review recent security activity. FYI: Apollo free tier loses live-agent support from 2026-07-14 (upgrade = paid, owner decision).
- **Meta (Facebook/Instagram) access token EXPIRED** (OAuthException 190, expired 2026-07-11 05:00 PDT): both approved Python posts failed to publish. Generate a new token in Meta Business settings, update `.env`, then re-run `Scripts/approval_executor.py`.
- Credentials not yet configured: copy `.env.example` to `.env` and fill in Gmail, SMTP, Twilio, LinkedIn, Odoo, Meta (Facebook/Instagram), and X values to activate the watchers, senders, and MCP servers.
- Odoo not yet running: `docker compose up -d` in /Odoo, create database "business", install Invoicing, then set ODOO_* in .env.
- Re-run `Scripts\register_tasks.ps1` to add the new AIEmployee-WeeklyAudit scheduled task.
- Cloud agent not yet deployed: follow Part 2–3 of [[START_AI_EMPLOYEE]] to provision the Oracle VM, pull this vault, and run `Cloud/setup_oracle_vm.sh`.

<!-- graph-links -->
## Related

- [[Company_Handbook]] · [[README]] · [[CLAUDE]] · [[Business_Profile]] · [[Personal_Profile]] · [[Content_Calendar]] · [[Social_Content_Calendar]] · [[Skills_Index]]
