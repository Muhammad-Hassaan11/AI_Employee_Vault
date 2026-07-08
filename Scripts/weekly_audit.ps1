# Weekly Business & Accounting Audit -> CEO Briefing
# ---------------------------------------------------
# Drops an audit task into /Needs_Action and invokes Claude headless to
# execute the /Skills/weekly-audit skill, producing /Briefings/CEO_Briefing_*.md.
# Scheduled weekly via Scripts\register_tasks.ps1 (AIEmployee-WeeklyAudit).
#
# Run manually:  powershell -File Scripts\weekly_audit.ps1

$VaultRoot = Split-Path -Parent $PSScriptRoot
Set-Location $VaultRoot

$Today = Get-Date -Format "yyyy-MM-dd"
$Now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$LogFile = Join-Path $VaultRoot ("Logs\" + $Today + ".md")
function Write-Log($msg) {
    $line = "- " + (Get-Date -Format "HH:mm:ss") + " [weekly-audit] " + $msg
    Add-Content -Path $LogFile -Value $line -Encoding utf8
    Write-Host $line
}

New-Item -ItemType Directory -Force (Join-Path $VaultRoot "Briefings") | Out-Null

# --- Create the audit task file ------------------------------------------
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$TaskFile = Join-Path $VaultRoot ("Needs_Action\" + $Stamp + "_weekly_audit.md")
$TaskContent = @"
---
type: weekly_audit
priority: high
status: pending
source: scheduler
created_at: $Now
---

# Weekly Business & Accounting Audit

Run the weekly-audit skill: gather Odoo accounting summary, social media
engagement, and operations stats from Logs/audit.jsonl, then write
/Briefings/CEO_Briefing_$Today.md.

## Status History
- ${Now}: Task created by weekly audit scheduler
"@
Set-Content -Path $TaskFile -Value $TaskContent -Encoding utf8
Write-Log "Created audit task: $(Split-Path -Leaf $TaskFile)"

# --- Invoke Claude headless -----------------------------------------------
$Prompt = @'
You are Atlas, the AI Employee. There is a weekly_audit task in /Needs_Action.
Follow /Skills/weekly-audit/SKILL.md exactly: create a plan in /Plans, gather
accounting data via the vault-odoo MCP tools, social engagement via the
vault-social MCP tools, and operations stats from Logs/audit.jsonl (each
section degrades gracefully if unavailable). Write the CEO briefing to
/Briefings, update Dashboard.md, log your work, and move the task file and
plan to /Done. This audit is read-only: do not send, post, or create
anything external.
'@

claude -p $Prompt --permission-mode acceptEdits
$ExitCode = $LASTEXITCODE
Write-Log "Claude audit run finished (exit $ExitCode)"

# --- Audit-trail entry ------------------------------------------------------
$Briefing = Join-Path $VaultRoot ("Briefings\CEO_Briefing_" + $Today + ".md")
$Status = "ok"
if (-not (Test-Path $Briefing)) { $Status = "failed" }
$Entry = @{ ts = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss"); component = "weekly-audit";
            action = "run"; status = $Status } | ConvertTo-Json -Compress
Add-Content -Path (Join-Path $VaultRoot "Logs\audit.jsonl") -Value $Entry -Encoding utf8
Write-Log "Weekly audit complete: $Status"
