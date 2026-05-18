$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Get-CfnLintExe {
    $pyVer = (& python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')").Trim()
    if ($env:APPDATA -and $pyVer -ne '') {
        $candidateAppData = Join-Path $env:APPDATA ("Python\Python$pyVer\Scripts\cfn-lint.exe")
        if (Test-Path $candidateAppData) { return $candidateAppData }
    }

    $userBase = (& python -c "import site; print(site.getuserbase())").Trim()
    if ($userBase -ne '') {
        $candidate0 = Join-Path (Join-Path $userBase 'Scripts') 'cfn-lint.exe'
        if (Test-Path $candidate0) { return $candidate0 }
    }

    $scriptsDir = (& python -c "import sysconfig; print(sysconfig.get_path('scripts'))").Trim()
    $candidate = Join-Path $scriptsDir 'cfn-lint.exe'
    if (Test-Path $candidate) { return $candidate }

    return $null
}

$cfnLint = Get-CfnLintExe
if (-not $cfnLint) {
    Write-Host "[X] cfn-lint.exe not found. Install with: python -m pip install cfn-lint" -ForegroundColor Red
    exit 1
}

$templates = @(
    'infrastructure/templates/api-stack.yaml',
    'infrastructure/templates/auth-stack.yaml',
    'infrastructure/templates/video-stack.yaml',
    'infrastructure/templates/edge-hosting-stack.yaml',
    'infrastructure/templates/github-deploy-role-stack.yaml',
    'infrastructure/templates/billing-alarm.yaml',
    'infrastructure/templates/rds-stack.yaml',
    'infrastructure/templates/media-cleanup-stack.yaml',
    'infrastructure/templates/payments-stack.yaml'
)

Push-Location $repoRoot
try {
    foreach ($t in $templates) {
        & $cfnLint --config-file .cfnlintrc $t
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host "[OK] cfn-lint passed" -ForegroundColor Green
} finally {
    Pop-Location
}

