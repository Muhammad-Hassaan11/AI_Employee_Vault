---
name: handle-approvals
aliases: ["handle-approvals skill"]
description: Review the human-in-the-loop approval queue in /Pending_Approval - report what is waiting, execute approved items via the approval executor, and archive rejected ones. Use when asked about pending approvals or to process the approval queue.
---

# Skill: Handle Approvals

## When to Use

- The user asks "what's waiting for my approval?"
- A scheduled run needs to process the approval queue
- After the user says they approved/rejected something

## How the Approval Workflow Works

1. Atlas drafts sensitive actions (emails, LinkedIn posts) as files in
   /Pending_Approval with `status: pending` in the frontmatter
2. The human reviews each file and edits the frontmatter to
   `status: approved` or `status: rejected`
3. Execution happens ONLY through `python Scripts/approval_executor.py`,
   which sends approved emails (SMTP), publishes approved LinkedIn posts
   (LinkedIn API), and archives rejected items to /Done

## Steps

1. List all .md files in /Pending_Approval
2. For each, read the frontmatter `type` and `status`
3. Report a summary to the user: what is pending, approved, rejected
4. If any items are approved or rejected, run:
   `python Scripts/approval_executor.py`
5. Report the execution results (they are appended to each file and logged)
6. Update Dashboard.md "Needs My Approval" count and log the action

## Rules

- NEVER change a status yourself — approval decisions belong to the human
- NEVER bypass the executor to send/publish directly

<!-- graph-links -->
## Related

- Index: [[Skills_Index]]
- Rules: [[Company_Handbook]]
- Board: [[Dashboard]]
- Related skill/doc: [[send-email skill]]
- Related skill/doc: [[social-post skill]]
