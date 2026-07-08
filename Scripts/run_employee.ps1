# Reasoning Loop for AI Employee Vault
# ------------------------------------
# Runs the watchers, then invokes Claude Code headless so Atlas processes
# everything in /Needs_Action per CLAUDE.md: create PLAN files in /Plans,
# execute using Skills, route sensitive actions to /Pending_Approval,
# archive to /Done, update Dashboard and Logs.
# Finally runs the approval executor for anything a human has approved.
#
# Run manually:            powershell -File Scripts\run_employee.ps1
# Or on a schedule via:    Scripts\register_tasks.ps1

$VaultRoot = Split-Path -Parent $PSScriptRoot
Set-Location $VaultRoot

$LogFile = Join-Path $VaultRoot ("Logs\" + (Get-Date -Format "yyyy-MM-dd") + ".md")
function Write-Log($msg) {
    $line = "- " + (Get-Date -Format "HH:mm:ss") + " [reasoning-loop] " + $msg
    Add-Content -Path $LogFile -Value $line -Encoding utf8
    Write-Host $line
}

Write-Log "Run started"

# --- Step 1: Run all watchers once (each exits cleanly if not configured) ---
python "$VaultRoot\Watchers\gmail_watcher.py"
python "$VaultRoot\Watchers\whatsapp_watcher.py"
python "$VaultRoot\Watchers\linkedin_watcher.py"
python "$VaultRoot\Watchers\filesystem_watcher.py"

# --- Step 2: If there is work, run the Claude reasoning loop -----------------
$Tasks = Get-ChildItem -Path "$VaultRoot\Needs_Action" -Filter *.md -File -ErrorAction SilentlyContinue
if ($Tasks -and $Tasks.Count -gt 0) {
    Write-Log ("Found " + $Tasks.Count + " task(s) in Needs_Action - invoking Claude")

    $Prompt = @'
You are Atlas, the AI Employee. Follow CLAUDE.md exactly:
1. For each file in /Needs_Action: read it and create /Plans/PLAN_[taskname].md describing the steps.
2. Execute each plan using the Agent Skills in /Skills (process-task, summarize-file, linkedin-post, send-email).
3. Any sensitive action (sending email/messages, publishing LinkedIn posts, payments, deletions) must be written as an action file in /Pending_Approval with status: pending - never executed directly.
4. Move completed task files and plans to /Done, update Dashboard.md, and log to /Logs.
'@

    claude -p $Prompt --permission-mode acceptEdits
    Write-Log "Claude reasoning run finished"
} else {
    Write-Log "No tasks in Needs_Action"
}

# --- Step 3: Execute anything a human has approved ---------------------------
python "$VaultRoot\Scripts\approval_executor.py"

Write-Log "Run complete"
