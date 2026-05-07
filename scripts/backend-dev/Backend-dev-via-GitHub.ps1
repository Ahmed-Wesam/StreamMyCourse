# Dispatches **deploy-backend-dev-only.yml** (Backend dev — Video + API only). See README.md.
#
# Usage:
#   .\Backend-dev-via-GitHub.ps1
#   .\Backend-dev-via-GitHub.ps1 main

param(
    [string]$Ref = ''
)

$gh = Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'
if (-not (Test-Path -LiteralPath $gh)) {
    $found = where.exe gh 2>$null | Select-Object -First 1
    if ($found) { $gh = $found.Trim() } else { Write-Error 'GitHub CLI (gh) not found.' ; exit 1 }
}

Push-Location (Split-Path $PSScriptRoot -Parent | Split-Path -Parent)
try {
    if (-not $Ref) {
        $branch = ''
        try { $branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch { }
        $Ref = if ($branch -and ($branch -ne 'HEAD')) { $branch } else { 'main' }
    }
    $wf = 'deploy-backend-dev-only.yml'
    & $gh workflow run $wf --ref $Ref
    Write-Host "Triggered workflow $wf for ref=$Ref — gh run list --workflow $wf"
} finally {
    Pop-Location
}
