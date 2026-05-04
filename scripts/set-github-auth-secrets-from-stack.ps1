#!/usr/bin/env pwsh
# Read Cognito auth stack + API stack outputs from AWS, then set GitHub Environment secrets via gh.
# Prereqs: aws CLI, gh CLI, gh auth login, StreamMyCourse-Auth-<env> and API stack deployed.
#
# Usage:
#   .\scripts\set-github-auth-secrets-from-stack.ps1 -Environment dev
#   .\scripts\set-github-auth-secrets-from-stack.ps1 -Environment dev -WhatIf
#   .\scripts\set-github-auth-secrets-from-stack.ps1 -Environment prod -GitHubEnvironment prod

param(
    [ValidateSet('dev', 'prod')]
    [string]$Environment = 'dev',
    [string]$Region = 'eu-west-1',
    [string]$GitHubEnvironment = '',
    [switch]$WhatIf,
    [switch]$SkipApiBaseUrl
)

$ErrorActionPreference = 'Stop'
if (-not $GitHubEnvironment) {
    $GitHubEnvironment = $Environment
}

function Resolve-AwsCli {
    if (Get-Command aws -ErrorAction SilentlyContinue) {
        return 'aws'
    }
    $p = "${env:ProgramFiles}\Amazon\AWSCLIV2\aws.exe"
    if (Test-Path $p) {
        return $p
    }
    throw 'AWS CLI not found.'
}

function Resolve-GhCli {
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        return 'gh'
    }
    foreach ($try in @(
            "${env:ProgramFiles}\GitHub CLI\gh.exe",
            "${env:LocalAppData}\Programs\GitHub CLI\gh.exe"
        )) {
        if (Test-Path $try) {
            return $try
        }
    }
    throw 'GitHub CLI (gh) not found. Install from https://cli.github.com/ and run gh auth login.'
}

function Get-CfnOutput {
    param([string]$StackName, [string]$OutputKey, [string]$AwsExe, [string]$AwsRegion)
    $v = & $AwsExe cloudformation describe-stacks `
        --stack-name $StackName `
        --region $AwsRegion `
        --query "Stacks[0].Outputs[?OutputKey=='$OutputKey'].OutputValue | [0]" `
        --output text 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "describe-stacks failed for $StackName : $v"
    }
    return ($v | Out-String).Trim()
}

$awsExe = Resolve-AwsCli
$ghExe = Resolve-GhCli

$authStack = "StreamMyCourse-Auth-$Environment"
$apiStack = if ($Environment -eq 'dev') {
    'streammycourse-api'
} else {
    'StreamMyCourse-Api-prod'
}

Write-Host "Auth stack: $authStack" -ForegroundColor Cyan
Write-Host "API stack:  $apiStack (ApiEndpoint -> VITE_API_BASE_URL)" -ForegroundColor Cyan
Write-Host "GitHub Environment for secrets: $GitHubEnvironment`n" -ForegroundColor Cyan

$userPoolId = Get-CfnOutput -StackName $authStack -OutputKey 'UserPoolId' -AwsExe $awsExe -AwsRegion $Region
$studentId = Get-CfnOutput -StackName $authStack -OutputKey 'StudentUserPoolClientId' -AwsExe $awsExe -AwsRegion $Region
$teacherId = Get-CfnOutput -StackName $authStack -OutputKey 'TeacherUserPoolClientId' -AwsExe $awsExe -AwsRegion $Region
$hosted = Get-CfnOutput -StackName $authStack -OutputKey 'HostedUIDomain' -AwsExe $awsExe -AwsRegion $Region

$apiUrl = $null
if (-not $SkipApiBaseUrl) {
    $apiUrl = Get-CfnOutput -StackName $apiStack -OutputKey 'ApiEndpoint' -AwsExe $awsExe -AwsRegion $Region
}

$sets = @(
    @{ Name = 'VITE_COGNITO_USER_POOL_ID'; Value = $userPoolId },
    @{ Name = 'VITE_COGNITO_STUDENT_CLIENT_ID'; Value = $studentId },
    @{ Name = 'VITE_COGNITO_TEACHER_CLIENT_ID'; Value = $teacherId },
    @{ Name = 'VITE_COGNITO_DOMAIN'; Value = $hosted }
)
if (-not $SkipApiBaseUrl) {
    $sets += @{ Name = 'VITE_API_BASE_URL'; Value = $apiUrl }
}

foreach ($s in $sets) {
    if ([string]::IsNullOrWhiteSpace($s.Value) -or $s.Value -eq 'None') {
        throw "Empty output for $($s.Name); check stack outputs."
    }
}

if ($WhatIf) {
    Write-Host "`n-WhatIf: no secrets written. Values preview:" -ForegroundColor Yellow
    $sets | ForEach-Object { Write-Host ("  {0}={1}" -f $_.Name, $_.Value) }
    exit 0
}

foreach ($s in $sets) {
    Write-Host ("Setting {0}..." -f $s.Name) -ForegroundColor Gray
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $ghExe
    $psi.Arguments = "secret set $($s.Name) --env $GitHubEnvironment"
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.StandardInput.Write($s.Value)
    $p.StandardInput.Close()
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    if ($p.ExitCode -ne 0) {
        throw "gh secret set $($s.Name) failed (exit $($p.ExitCode)): $err"
    }
    Write-Host "OK $($s.Name)" -ForegroundColor Green
}

Write-Host "`nDone. Push to main to run the Deploy workflow (student + teacher web rebuild)." -ForegroundColor Cyan
Write-Host "  gh run list --workflow Deploy --limit 5" -ForegroundColor DarkGray
