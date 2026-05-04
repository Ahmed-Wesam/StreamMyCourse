# Deploy the GitHub OIDC deploy IAM stack (CloudFormation). NOT used by GitHub Actions — run locally
# with admin credentials when bootstrapping or when github-deploy-role-stack.yaml changes.
#
# Usage (repo root):
#   .\scripts\deploy-github-iam-stack.ps1
#   $env:GITHUB_IAM_STACK_NAME = 'my-stack'; .\scripts\deploy-github-iam-stack.ps1
#
# Extra args are forwarded to aws cloudformation deploy (e.g. -ParameterOverrides ...).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AwsArgs
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..') | ForEach-Object { $_.Path }
$StackName = if ($env:GITHUB_IAM_STACK_NAME) { $env:GITHUB_IAM_STACK_NAME } else { 'StreamMyCourse-GitHubDeployIam' }
$Template = Join-Path $Root 'infrastructure\templates\github-deploy-role-stack.yaml'

if (-not (Test-Path -LiteralPath $Template)) {
    throw "Missing template: $Template"
}

$awsExe = $null
if (Get-Command aws -ErrorAction SilentlyContinue) {
    $awsExe = 'aws'
} elseif (Test-Path "${env:ProgramFiles}\Amazon\AWSCLIV2\aws.exe") {
    $awsExe = "${env:ProgramFiles}\Amazon\AWSCLIV2\aws.exe"
} else {
    throw 'AWS CLI not found.'
}

Write-Host "Deploying stack: $StackName"
Push-Location $Root
try {
    $deployArgs = @(
        'cloudformation', 'deploy',
        '--stack-name', $StackName,
        '--template-file', 'infrastructure/templates/github-deploy-role-stack.yaml',
        '--capabilities', 'CAPABILITY_NAMED_IAM'
    ) + $AwsArgs
    & $awsExe @deployArgs
    if ($LASTEXITCODE -ne 0) {
        throw "aws cloudformation deploy failed (exit $LASTEXITCODE)"
    }

    Write-Host '[OK] Stack deployed. Role ARN:'
    & $awsExe cloudformation describe-stacks `
        --stack-name $StackName `
        --query "Stacks[0].Outputs[?OutputKey=='GitHubDeployRoleArn'].OutputValue" `
        --output text
}
finally {
    Pop-Location
}
