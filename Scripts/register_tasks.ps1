# Register AI Employee scheduled tasks in Windows Task Scheduler.
# Run from an elevated (or normal) PowerShell:
#     powershell -ExecutionPolicy Bypass -File Scripts\register_tasks.ps1
# Remove them later with:
#     powershell -File Scripts\register_tasks.ps1 -Unregister

param([switch]$Unregister)

$VaultRoot = Split-Path -Parent $PSScriptRoot
$Python = "python"

$Tasks = @(
    @{ Name = "AIEmployee-GmailWatcher";    Cmd = "$Python `"$VaultRoot\Watchers\gmail_watcher.py`"";    Minutes = 15 },
    @{ Name = "AIEmployee-WhatsAppWatcher"; Cmd = "$Python `"$VaultRoot\Watchers\whatsapp_watcher.py`""; Minutes = 15 },
    @{ Name = "AIEmployee-LinkedInWatcher"; Cmd = "$Python `"$VaultRoot\Watchers\linkedin_watcher.py`""; Minutes = 60 },
    @{ Name = "AIEmployee-ApprovalExecutor"; Cmd = "$Python `"$VaultRoot\Scripts\approval_executor.py`""; Minutes = 10 },
    @{ Name = "AIEmployee-ReasoningLoop";   Cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$VaultRoot\Scripts\run_employee.ps1`""; Minutes = 30 }
)

foreach ($t in $Tasks) {
    if ($Unregister) {
        try {
            Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction Stop
            Write-Host ("Removed: " + $t.Name)
        } catch {
            Write-Host ("Not found: " + $t.Name)
        }
        continue
    }

    $parts = $t.Cmd -split " ", 2
    $action = New-ScheduledTaskAction -Execute $parts[0] -Argument $parts[1] -WorkingDirectory $VaultRoot
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
        -RepetitionInterval (New-TimeSpan -Minutes $t.Minutes) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries `
        -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 25)

    Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger `
        -Settings $settings -Description "AI Employee Vault automation" -Force | Out-Null
    Write-Host ("Registered: " + $t.Name + " (every " + $t.Minutes + " min)")
}

if (-not $Unregister) {
    Write-Host ""
    Write-Host "All AI Employee tasks registered. View them in Task Scheduler under \ or with:"
    Write-Host "  Get-ScheduledTask -TaskName 'AIEmployee-*'"
}
