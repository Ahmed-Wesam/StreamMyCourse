#!/usr/bin/env pwsh
# Print Cognito auth stack CloudFormation outputs and map them to GitHub Actions secrets / local .env.
# Usage: .\scripts\print-auth-stack-outputs.ps1 [-Environment dev|prod] [-Region eu-west-1]
param(
    [ValidateSet('dev', 'prod')]
    [string]$Environment = 'dev',
    [string]$Region = 'eu-west-1'
)

$ErrorActionPreference = 'Stop'
$stack = "StreamMyCourse-Auth-$Environment"

$awsExe = $null
if (Get-Command aws -ErrorAction SilentlyContinue) {
    $awsExe = 'aws'
} elseif (Test-Path "${env:ProgramFiles}\Amazon\AWSCLIV2\aws.exe") {
    $awsExe = "${env:ProgramFiles}\Amazon\AWSCLIV2\aws.exe"
}
if (-not $awsExe) {
    throw 'AWS CLI not found. Add aws to PATH or install AWS CLI v2.'
}

$raw = & $awsExe cloudformation describe-stacks --stack-name $stack --region $Region --output json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $raw -ForegroundColor Red
    exit $LASTEXITCODE
}

$json = $raw | ConvertFrom-Json
$outputs = $json.Stacks[0].Outputs
if (-not $outputs) {
    Write-Host "Stack $stack has no Outputs." -ForegroundColor Red
    exit 1
}

function Out-Val([string]$key) {
    ($outputs | Where-Object { $_.OutputKey -eq $key }).OutputValue
}

$userPoolId = Out-Val 'UserPoolId'
$studentId = Out-Val 'StudentUserPoolClientId'
$teacherId = Out-Val 'TeacherUserPoolClientId'
$hosted = Out-Val 'HostedUIDomain'

Write-Host "`n=== CloudFormation: $stack ($Region) ===" -ForegroundColor Cyan
Write-Host "UserPoolId                  : $userPoolId"
Write-Host "StudentUserPoolClientId     : $studentId"
Write-Host "TeacherUserPoolClientId     : $teacherId"
Write-Host "HostedUIDomain              : $hosted"

Write-Host "`n=== GitHub Actions secrets (repository or Environment) ===" -ForegroundColor Cyan
Write-Host "VITE_COGNITO_USER_POOL_ID       = $userPoolId"
Write-Host "VITE_COGNITO_STUDENT_CLIENT_ID  = $studentId"
Write-Host "VITE_COGNITO_TEACHER_CLIENT_ID  = $teacherId"
Write-Host "VITE_COGNITO_DOMAIN             = $hosted"

Write-Host "`n=== frontend/.env (local dev; do not commit) ===" -ForegroundColor Cyan
Write-Host "VITE_COGNITO_USER_POOL_ID=$userPoolId"
Write-Host "VITE_COGNITO_USER_POOL_CLIENT_ID=$studentId   # student app; use teacher client id when running teacher entrypoint"
Write-Host "VITE_COGNITO_DOMAIN=$hosted"

Write-Host "`nNext: set GitHub Environment secrets (see scripts/set-github-auth-secrets-from-stack.ps1), then push main - Deploy workflow rebuilds student + teacher SPAs." -ForegroundColor Yellow
Write-Host 'Manual Deploy Web (manual) workflows are optional fallbacks only.' -ForegroundColor DarkGray
