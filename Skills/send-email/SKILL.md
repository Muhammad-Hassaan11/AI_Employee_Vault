---
name: send-email
description: Draft an email reply or outreach message and route it through /Pending_Approval; after human approval it is sent via the vault-email MCP server (send_email tool) or the approval executor. Use whenever a task requires emailing someone — replies to Gmail watcher tasks, follow-ups, or outreach.
---

# Skill: Send Email

## When to Use

Any task that requires sending an email: replying to an email task created
by the Gmail watcher, following up with a client, or outreach.

## Steps

1. Read the task file for context (sender, subject, what they need)
2. Draft the email: polite, professional, concise (per Company_Handbook.md)
3. Save the draft to /Pending_Approval/EMAIL_[slug].md using the format below
4. Do NOT send it yet — the Company Handbook forbids sending any message
   without human approval
5. After a human sets `status: approved`, the email is sent by either:
   - Scripts/approval_executor.py (runs on schedule), or
   - the `send_email` tool on the vault-email MCP server with approved=true
6. Move the task file and plan to /Done, update Dashboard.md, log the action

## Approval File Format

```
---
type: email
status: pending
to: [recipient email address]
subject: [subject line]
created_at: [YYYY-MM-DD HH:MM:SS]
---
[The plain-text email body exactly as it should be sent]
```

## Rules

- NEVER set status to approved yourself — only the human does that
- NEVER call send_email with approved=true unless the human already
  approved the draft in /Pending_Approval
- Keep the body plain text; it is sent verbatim
