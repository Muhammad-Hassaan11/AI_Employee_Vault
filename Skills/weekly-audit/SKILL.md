---
name: weekly-audit
aliases: ["weekly-audit skill"]
description: Run the weekly business + accounting audit and generate the CEO briefing. Use when a task asks for a weekly audit, business review, or CEO briefing.
---

# Weekly Business & Accounting Audit → CEO Briefing

Produce `/Briefings/CEO_Briefing_[YYYY-MM-DD].md` covering the last 7 days.
This is a READ-ONLY audit: gather data, analyze, write the briefing. Never
create, modify, or post anything external during an audit.

## Step 1: Gather data (degrade gracefully)

Collect each section independently. If a source is unavailable (server down,
credentials missing), record "unavailable: <reason>" for that section and
continue — never abort the whole audit because one source failed.

1. **Accounting (Odoo)**: call the `vault-odoo` MCP tools:
   - `accounting_summary` with days=7 (revenue, expenses, receivables)
   - `list_invoices` days=7 and `list_expenses` days=7 for detail
2. **Social media**: call the `vault-social` MCP tool `social_summary`
   (Facebook + Instagram + X engagement).
3. **Operations**: read `/Logs/audit.jsonl` and count, for the last 7 days:
   tasks created, actions executed, approvals executed/rejected, failures
   (status: failed) and retries. List any repeated failures.
4. **Workload**: count files currently in /Needs_Action, /Pending_Approval,
   and items completed this week in /Done.
5. **Context**: read /Business/Business_Profile.md and
   /Personal/Personal_Profile.md so recommendations fit both domains.

## Step 2: Write the briefing

Create `/Briefings/CEO_Briefing_[YYYY-MM-DD].md`:

```markdown
# CEO Briefing - Week ending [date]

## Executive Summary
[3-5 sentences: financial position, notable wins, top risk]

## Financials (Odoo, last 7 days)
- Revenue invoiced / expenses / net
- Outstanding receivables & payables
- Notable invoices or bills

## Social Media
- Per-platform engagement (or "not configured")
- What content performed best

## Operations
- Tasks processed, approvals executed/rejected, error count
- Watcher/system health issues from audit.jsonl

## Bottlenecks & Risks
[Anything stuck in /Pending_Approval, repeated failures, unpaid invoices]

## Recommendations
[3 concrete, prioritized suggestions for next week]
```

## Step 3: Complete

- Update /Dashboard.md (Recent Activity + link to the briefing)
- Log to /Logs/[today].md and append an audit entry meaning
  "weekly_audit completed" (the run script does this automatically)
- Move the audit task file and plan to /Done

<!-- graph-links -->
## Related

- Index: [[Skills_Index]]
- Rules: [[Company_Handbook]]
- Board: [[Dashboard]]
- Related skill/doc: [[Business_Profile]]
