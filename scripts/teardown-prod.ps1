# Windows wrapper for scripts/teardown-prod.sh (Git Bash / WSL).
# Usage: .\scripts\teardown-prod.ps1 [--dry-run] [--confirm] [--skip-missing] [--manifest-out PATH]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Convert-ToBashPath([string] $Path) {
    $unix = $Path -replace '\\', '/'
    if ($unix -match '^([A-Za-z]):(.*)$') {
        return ('/' + $Matches[1].ToLower() + $Matches[2])
    }
    return $unix
}

function Quote-BashArg([string] $Arg) {
    return "'" + ($Arg -replace "'", "'\\''") + "'"
}

$repoUnix = Convert-ToBashPath $repoRoot
$argSuffix = ''
if ($RemainingArgs.Count -gt 0) {
    $quoted = $RemainingArgs | ForEach-Object { Quote-BashArg $_ }
    $argSuffix = ' ' + ($quoted -join ' ')
}

Push-Location $repoRoot
try {
    bash -lc "cd '$repoUnix'; ./scripts/teardown-prod.sh$argSuffix"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
