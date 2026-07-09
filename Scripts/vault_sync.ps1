# Vault sync (Local/Windows side) - Platinum "Delegation via Synced Vault".
#
# Pulls the Cloud agent's drafts/updates and pushes local changes
# (approvals, Dashboard, Done archive). Secrets never sync - .env, tokens,
# credentials and watcher state are gitignored.
#
# Usage:  powershell -File Scripts\vault_sync.ps1 pull
#         powershell -File Scripts\vault_sync.ps1 push
#         powershell -File Scripts\vault_sync.ps1        (full cycle)
param([string]$Mode = "full")

$VaultRoot = Split-Path -Parent $PSScriptRoot
Set-Location $VaultRoot
$Agent = if ($env:AGENT_ROLE) { $env:AGENT_ROLE } else { "local" }

function Write-Log($msg) {
    $line = "- " + (Get-Date -Format "HH:mm:ss") + " [vault-sync/$Agent] " + $msg
    Add-Content -Path (Join-Path $VaultRoot ("Logs\" + (Get-Date -Format "yyyy-MM-dd") + ".md")) -Value $line -Encoding utf8
    Write-Host $line
}

git remote get-url origin *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Log "No git remote 'origin' configured - skipping sync (single-machine mode)"
    exit 0
}
$Branch = (git rev-parse --abbrev-ref HEAD).Trim()

if ($Mode -eq "pull" -or $Mode -eq "full") {
    git pull --rebase --autostash origin $Branch
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Pulled latest vault state"
    } else {
        git rebase --abort 2>$null
        Write-Log "WARNING: pull failed (conflict or network) - continuing with local state"
    }
}

if ($Mode -eq "push" -or $Mode -eq "full") {
    git add -A
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Nothing to push"
    } else {
        git commit -m ("sync(" + $Agent + "): vault state " + (Get-Date -Format "yyyy-MM-dd HH:mm")) --quiet
        git push origin $Branch
        if ($LASTEXITCODE -ne 0) {
            git pull --rebase --autostash origin $Branch
            git push origin $Branch
        }
        if ($LASTEXITCODE -eq 0) { Write-Log "Pushed vault changes" }
        else { Write-Log "WARNING: push failed - changes remain committed locally" }
    }
}
