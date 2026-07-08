---
name: social-post
aliases: ["social-post skill"]
description: Draft Facebook, Instagram, or X (Twitter) posts for human approval, and generate engagement summaries. Use for any task about posting to or reviewing social media.
---

# Social Media Posts (Facebook / Instagram / X)

Publishing is SENSITIVE: never post directly. Draft to /Pending_Approval;
the approval executor publishes after a human approves.

## Drafting a post

1. Read /Business/Business_Profile.md for voice and offer context (and
   /LinkedIn/Content_Calendar.md if the task references the calendar).
2. Write the post. Constraints:
   - `tweet`: max 280 characters
   - `instagram_post`: requires a public `image_url` in the frontmatter
   - `facebook_post`: plain text
3. Create `/Pending_Approval/[PLATFORM]_[slug].md`:

```markdown
---
type: facebook_post | instagram_post | tweet
status: pending
domain: business
image_url: https://...        (instagram_post only)
created_at: YYYY-MM-DD HH:MM:SS
---

<post text - published verbatim>
```

4. Update Dashboard.md (Awaiting Approval section) and log to /Logs.
5. Move the originating task file and plan to /Done. The post itself waits
   for the human; do NOT call the vault-social post tools with approved=true.

## Engagement summary

Use the vault-social MCP tools: `facebook_summary`, `instagram_summary`,
`twitter_summary`, or `social_summary` for all platforms at once. Platforms
without credentials report an ERROR line - include that as "not configured"
rather than failing the task. Write the summary into the task's output
(or the CEO briefing when called from the weekly-audit skill).

<!-- graph-links -->
## Related

- Index: [[Skills_Index]]
- Rules: [[Company_Handbook]]
- Board: [[Dashboard]]
- Related skill/doc: [[linkedin-post skill]]
- Related skill/doc: [[handle-approvals skill]]
