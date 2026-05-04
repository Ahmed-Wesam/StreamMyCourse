# Apply version-controlled IAM inline policies to an existing GitHub Actions OIDC deploy role.
# Prefer .\scripts\deploy-github-iam-stack.ps1 for full role + OIDC bootstrap (CloudFormation).
# Run locally (with admin IAM credentials) BEFORE pushing workflow or policy changes that
# need new permissions — otherwise Deploy can fail mid-pipeline (e.g. ACM in us-east-1).
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

Write-Host "Applying inline policies to IAM role: $RoleName"
Push-Location $Root
try {
    & $awsExe iam get-role --role-name $RoleName | Out-Null

    & $awsExe iam put-role-policy `
        --role-name $RoleName `
        --policy-name StreamMyCourseGitHubDeployBackend `
        --policy-document file://infrastructure/iam-policy-github-deploy-backend.json

    & $awsExe iam put-role-policy `
        --role-name $RoleName `
        --policy-name StreamMyCourseGitHubDeployWeb `
        --policy-document file://infrastructure/iam-policy-github-deploy-web.json
}
finally {
    Pop-Location
}

Write-Host "[OK] StreamMyCourseGitHubDeployBackend + StreamMyCourseGitHubDeployWeb updated on $RoleName"
