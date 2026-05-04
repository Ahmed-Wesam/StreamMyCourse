# Deploy one environment's backend: Video (S3) + API (Lambda, API Gateway, DynamoDB).
# Student/teacher SPAs and ACM: use deploy.ps1 -Template edge-hosting (see infrastructure/docs/edge-hosting-migration.md).
#
# Naming convention (mirrored dev / integ / prod):
#   StreamMyCourse-Video-{env}
#   StreamMyCourse-Api-{env}     (prod, integ)
#   streammycourse-api           (legacy dev stack name — same resources as StreamMyCourse-Api-dev would be)
#
# Usage:
#   .\deploy-environment.ps1 -Environment prod
#   .\deploy-environment.ps1 -Environment integ
#   .\deploy-environment.ps1 -Environment dev
#   .\deploy-environment.ps1 -Environment dev -NewDevApiStack   # only if streammycourse-api was removed (avoids DynamoDB name clash)
#
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('dev', 'integ', 'prod')]
    [string] $Environment,

    [Parameter(Mandatory = $false)]
    [string] $Region = 'eu-west-1',

    # Use StreamMyCourse-Api-dev instead of legacy stack streammycourse-api (do not use while streammycourse-api exists)
    [Parameter(Mandatory = $false)]
    [switch] $NewDevApiStack
)

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$awsInstallDir = 'C:\Program Files\Amazon\AWSCLIV2'
if (Test-Path (Join-Path $awsInstallDir 'aws.exe')) {
    if ($env:Path -notlike "*${awsInstallDir}*") {
        $env:Path = "${awsInstallDir};${env:Path}"
    }
}

$videoStack = "StreamMyCourse-Video-$Environment"
Write-Host "=== 1/2 Video stack: $videoStack ===" -ForegroundColor Cyan
& "$here\deploy.ps1" -Template video -StackName $videoStack -Environment $Environment -Region $Region
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$bucketJson = aws cloudformation describe-stacks --stack-name $videoStack --region $Region --query 'Stacks[0].Outputs' --output json | ConvertFrom-Json
$videoBucket = ($bucketJson | Where-Object { $_.OutputKey -eq 'BucketName' }).OutputValue
$bucketUrl = ($bucketJson | Where-Object { $_.OutputKey -eq 'BucketURL' }).OutputValue
if (-not $videoBucket) {
    Write-Host "[X] Could not read BucketName from $videoStack" -ForegroundColor Red
    exit 1
}

$apiStack = if ($Environment -eq 'prod') {
    'StreamMyCourse-Api-prod'
} elseif ($Environment -eq 'integ') {
    'StreamMyCourse-Api-integ'
} elseif ($NewDevApiStack) {
    'StreamMyCourse-Api-dev'
} else {
    'streammycourse-api'
}

$cors = if ($Environment -eq 'prod') {
    'https://app.streammycourse.click,https://teach.streammycourse.click,http://localhost:5173,http://localhost:5174'
} elseif ($Environment -eq 'integ') {
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174'
} else {
    'https://dev.streammycourse.click,https://teach.dev.streammycourse.click,http://localhost:5173,http://localhost:5174'
}

$gatewayResponseOrigin = if ($Environment -eq 'prod') {
    'https://app.streammycourse.click'
} else {
    'http://localhost:5173'
}

Write-Host "=== 2/2 API stack: $apiStack (video bucket: $videoBucket) ===" -ForegroundColor Cyan
& "$here\deploy.ps1" -Template api -StackName $apiStack -Region $Region -Environment $Environment `
    -VideoBucketName $videoBucket `
    -VideoUrl $bucketUrl `
    -CorsAllowOrigin $cors `
    -GatewayResponseAllowOrigin $gatewayResponseOrigin

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[OK] Backend for $Environment deployed. ApiEndpoint:" -ForegroundColor Green
aws cloudformation describe-stacks --stack-name $apiStack --region $Region --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text
Write-Host "Use that value as VITE_API_BASE_URL when building the SPA for this environment (deploy.ps1 -Template web -ApiBaseUrl ...)." -ForegroundColor Gray
