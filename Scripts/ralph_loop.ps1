# Ralph Wiggum Loop Orchestrator
# ------------------------------
# Keeps Claude working autonomously until a task is complete: writes the
# loop state file, then invokes Claude headless. The Stop hook
# (Scripts\ralph_stop_hook.py, registered in .claude\settings.json)
# intercepts every exit attempt and re-injects the prompt until Claude's
# output contains the completion promise or max iterations is reached.
#
# Usage:
#   powershell -File Scripts\ralph_loop.ps1 `
#       -Prompt "Process all files in /Needs_Action, move to /Done when complete" `
#       -CompletionPromise "TASK_COMPLETE" -MaxIterations 10

param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [string]$CompletionPromise = "TASK_COMPLETE",
    [int]$MaxIterations = 10
)

$VaultRoot = Split-Path -Parent $PSScriptRoot
Set-Location $VaultRoot

$StateDir = Join-Path $VaultRoot "Scripts\.ralph"
New-Item -ItemType Directory -Force $StateDir | Out-Null
$State = @{
    active             = $true
    prompt             = $Prompt
    completion_promise = $CompletionPromise
    max_iterations     = $MaxIterations
    iteration          = 0
    started_at         = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
}
$StateFile = Join-Path $StateDir "state.json"
$State | ConvertTo-Json | Set-Content -Path $StateFile -Encoding utf8

$LogFile = Join-Path $VaultRoot ("Logs\" + (Get-Date -Format "yyyy-MM-dd") + ".md")
Add-Content -Path $LogFile -Encoding utf8 -Value ("- " + (Get-Date -Format "HH:mm:ss") + " [ralph-loop] Started (max $MaxIterations iterations): $Prompt")

$FullPrompt = $Prompt + "`n`nWhen the task is fully complete, end your reply with the exact phrase: " + $CompletionPromise

claude -p $FullPrompt --permission-mode acceptEdits

# Safety: deactivate the loop in case the run ended abnormally
$Final = Get-Content $StateFile -Raw | ConvertFrom-Json
if ($Final.active) {
    $Final.active = $false
    $Final | ConvertTo-Json | Set-Content -Path $StateFile -Encoding utf8
}
Add-Content -Path $LogFile -Encoding utf8 -Value ("- " + (Get-Date -Format "HH:mm:ss") + " [ralph-loop] Ended after $($Final.iteration) blocked exit(s); reason: $($Final.finish_reason)")
Write-Host "Ralph loop finished. Iterations: $($Final.iteration). Reason: $($Final.finish_reason)"
