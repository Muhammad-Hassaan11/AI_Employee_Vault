---
name: linkedin-post
aliases: ["linkedin-post skill"]
description: Draft a sales-oriented LinkedIn post about the business and route it to /Pending_Approval for human review before publishing. Use for any task about creating, drafting, or scheduling LinkedIn content (e.g. tasks created by the LinkedIn watcher from the content calendar).
---

# Skill: LinkedIn Post

## When to Use

Any task asking for a LinkedIn post to be created — especially tasks from
`Watchers/linkedin_watcher.py` with type `linkedin_post`.

## Steps

1. Read the task to get the topic and scheduled date
2. Read /LinkedIn/Content_Calendar.md "Posting Guidelines" for voice rules
3. Draft the post:
   - Hook in the first line (this is all LinkedIn shows before "…see more")
   - 3-6 short paragraphs or a short list; practical, no hype
   - Clear call-to-action at the end (DM us / book a call)
   - 3-5 relevant hashtags on the last line
4. Save the draft to /Pending_Approval/LINKEDIN_[slug].md using the format below
5. Do NOT publish it yourself — Scripts/approval_executor.py publishes it
   after the human sets `status: approved`
6. Move the task file and plan to /Done, update Dashboard.md, log the action

## Approval File Format

```
---
type: linkedin_post
status: pending
topic: [topic from the task]
created_at: [YYYY-MM-DD HH:MM:SS]
---
[The full post text exactly as it should appear on LinkedIn]
```

## Rules

- NEVER set status to approved yourself — only the human does that
- One post per file; the body is published verbatim, so no extra headings

<!-- graph-links -->
## Related

- Index: [[Skills_Index]]
- Rules: [[Company_Handbook]]
- Board: [[Dashboard]]
- Related skill/doc: [[Content_Calendar]]
- Related skill/doc: [[social-post skill]]
