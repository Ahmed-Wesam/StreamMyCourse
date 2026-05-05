# Apply version-controlled IAM inline policies to an existing GitHub Actions OIDC deploy role.
# Prefer .\scripts\deploy-github-iam-stack.ps1 for full role + OIDC bootstrap (CloudFormation).
# Run locally (with admin IAM credentials) BEFORE pushing workflow or policy changes that
# need new permissions — otherwise Deploy can fail mid-pipeline (e.g. ACM in us-east-1).
#
# Policy JSON uses YOUR_AWS_ACCOUNT_ID in ARNs; this script replaces it with the account id
# from aws sts get-caller-identity before iam put-role-policy (raw repo JSON is not valid IAM).
#
# Usage (repo root):
#   .\scripts\apply-github-deploy-role-policies.ps1
#   $env:GITHUB_DEPLOY_ROLE_NAME = 'my-role'; .\scripts\apply-github-deploy-role-policies.ps1
param(
    [string]$RoleName = $(if ($env:GITHUB_DEPLOY_ROLE_NAME) { $env:GITHUB_DEPLOY_ROLE_NAME } else { 'StreamMyCourseGitHubDeployWeb' })
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..') | ForEach-Object { $_.Path }
$BackendDoc = Join-Path $Root 'infrastructure\iam-policy-github-deploy-backend.json'
$WebDoc = Join-Path $Root 'infrastructure\iam-policy-github-deploy-web.json'

foreach ($f in @($BackendDoc, $WebDoc)) {
    if (-not (Test-Path -LiteralPath $f)) {
        throw "Missing policy file: $f"
    }
}

$awsExe = $null
if (Get-Command aws -ErrorAction SilentlyContinue) {
    $awsExe = 'aws'
} elseif (Test-Path "${env:ProgramFiles}\Amazon\AWSCLIV2\aws.exe") {
    $awsExe = "${env:ProgramFiles}\Amazon\AWSCLIV2\aws.exe"
} else {
    throw 'AWS CLI not found.'
}

$accountId = (& $awsExe sts get-caller-identity --query Account --output text).Trim()
if (-not $accountId) { throw 'Could not resolve AWS account id (sts get-caller-identity).' }

function Expand-PolicyTemplate([string]$Path) {
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return $raw.Replace('YOUR_AWS_ACCOUNT_ID', $accountId)
}

function ConvertTo-AwsCliFileUri([string]$fullPath) {
    $n = $fullPath -replace '\\', '/'
    if ($n -match '^[A-Za-z]:') {
        return "file://$n"
    }
    return "file:///$($n.TrimStart('/'))"
}

Write-Host "Applying inline policies to IAM role: $RoleName (substituting YOUR_AWS_ACCOUNT_ID -> $accountId)"
Push-Location $Root
$tmpBackend = $null
$tmpWeb = $null
try {
    & $awsExe iam get-role --role-name $RoleName | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "iam get-role failed for $RoleName" }

    $tmpBackend = Join-Path $env:TEMP "github-deploy-backend-$PID.json"
    $tmpWeb = Join-Path $env:TEMP "github-deploy-web-$PID.json"
    [IO.File]::WriteAllText($tmpBackend, (Expand-PolicyTemplate $BackendDoc), [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText($tmpWeb, (Expand-PolicyTemplate $WebDoc), [Text.UTF8Encoding]::new($false))

    $uriBackend = ConvertTo-AwsCliFileUri $tmpBackend
    $uriWeb = ConvertTo-AwsCliFileUri $tmpWeb

    & $awsExe iam put-role-policy `
        --role-name $RoleName `
        --policy-name StreamMyCourseGitHubDeployBackend `
        --policy-document $uriBackend
    if ($LASTEXITCODE -ne 0) { throw 'iam put-role-policy (StreamMyCourseGitHubDeployBackend) failed' }

    & $awsExe iam put-role-policy `
        --role-name $RoleName `
        --policy-name StreamMyCourseGitHubDeployWeb `
        --policy-document $uriWeb
    if ($LASTEXITCODE -ne 0) { throw 'iam put-role-policy (StreamMyCourseGitHubDeployWeb) failed' }
}
finally {
    Pop-Location
    foreach ($p in @($tmpBackend, $tmpWeb)) {
        if ($p -and (Test-Path -LiteralPath $p)) { Remove-Item -LiteralPath $p -Force }
    }
}

Write-Host "[OK] StreamMyCourseGitHubDeployBackend + StreamMyCourseGitHubDeployWeb updated on $RoleName"
