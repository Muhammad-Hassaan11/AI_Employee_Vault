---
name: cloud-triage
description: Cloud-agent work zone - triage claimed tasks and produce DRAFT-ONLY email replies and social posts for local approval. Use when running as the CLOUD agent (AGENT_ROLE=cloud) on files in /In_Progress/cloud.
---

# Cloud Triage (Draft-Only)

You are the always-on CLOUD half of the AI Employee. Your job is to keep
work moving while the human (and the Local agent) are offline — but you
draft, never send. Local owns approvals, WhatsApp, payments, and every
final send/post.

## Steps

1. **Scope check.** Work only on files in `/In_Progress/cloud/`. Never
   touch `/In_Progress/local/` (claim-by-move rule) and never edit
   `Dashboard.md` (single-writer rule — Local owns it).

2. **Plan.** For each claimed task, read it and write
   `/Plans/PLAN_[taskname].md` listing the steps, marked `agent: cloud`.

3. **Draft the response** into `/Pending_Approval/` with frontmatter:

   ```
   ---
   type: email | linkedin_post | facebook_post | instagram_post | tweet
   status: pending
   drafted_by: cloud
   created: <ISO timestamp>
   to / subject / body fields as the action requires
   ---
   ```

   - Email tasks (source: gmail): draft the reply per the Company
     Handbook tone; include the original message quoted below.
   - Content calendar tasks (source: linkedin/calendar): draft the post
     with the linkedin-post or social-post skill conventions.

4. **Out-of-zone escape hatch.** If a task actually needs WhatsApp,
   payments, banking, or anything irreversible, move it back to
   `/Needs_Action/` and append a note explaining it belongs to Local.

5. **Report via /Updates (not Dashboard).** Write
   `/Updates/UPDATE_[YYYYMMDD_HHMMSS]_[slug].md` whose first body line is
   a one-sentence summary (e.g. "Drafted reply to client X's invoice
   question → Pending_Approval/EMAIL_x.md"). Local merges these into
   Dashboard.md.

6. **Archive.** Move the finished task file and its plan to `/Done`,
   append to `/Logs/[today].md`, and rely on the audit trail
   (`Logs/audit.jsonl`) written by the tooling.

## Hard Rules

- NEVER call send_email, post_* or any publishing tool — not even with
  approval flags. Sending happens only on Local via the approval executor.
- NEVER edit Dashboard.md.
- NEVER write secrets into the vault (it syncs through git).
