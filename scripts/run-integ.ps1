param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('dev', 'integ', 'prod')]
    [string] $Environment = 'integ',

    [Parameter(Mandatory = $false)]
    [string] $Region = 'eu-west-1',

    # Skip backend deployment and only run tests against an existing stack.
    [Parameter(Mandatory = $false)]
    [switch] $SkipDeploy,

    # Optional: a Cognito JWT (ID or access token). Enables the bearer-only /users/me test.
    [Parameter(Mandatory = $false)]
    [string] $CognitoJwt = '',

    # Extra args forwarded to pytest (e.g. "-k users_me -q").
    [Parameter(Mandatory = $false)]
    [string] $PytestArgs = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

# Match infrastructure/deploy-environment.ps1: auto-add common AWS CLI v2 install dir.
$awsInstallDir = 'C:\Program Files\Amazon\AWSCLIV2'
if (Test-Path (Join-Path $awsInstallDir 'aws.exe')) {
    if ($env:Path -notlike "*${awsInstallDir}*") {
        $env:Path = "${awsInstallDir};${env:Path}"
    }
}

function Require-Command([string] $Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command '$Name' not found on PATH. Install it and retry."
    }
}

Require-Command 'python'
Require-Command 'aws'

Push-Location $repoRoot
try {
    if (-not $SkipDeploy) {
        Write-Host "=== Deploy backend ($Environment, $Region) ===" -ForegroundColor Cyan
        & "$repoRoot\infrastructure\deploy-environment.ps1" -Environment $Environment -Region $Region
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    $apiStack = if ($Environment -eq 'prod') { 'StreamMyCourse-Api-prod' } elseif ($Environment -eq 'integ') { 'StreamMyCourse-Api-integ' } else { 'streammycourse-api' }
    $videoStack = "StreamMyCourse-Video-$Environment"

    Write-Host "=== Discover stack outputs ===" -ForegroundColor Cyan
    $apiBaseUrl = (aws cloudformation describe-stacks --stack-name $apiStack --region $Region --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text).Trim()
    if (-not $apiBaseUrl) { throw "Could not read ApiEndpoint from stack $apiStack" }

    $videoBucket = (aws cloudformation describe-stacks --stack-name $videoStack --region $Region --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text).Trim()
    if (-not $videoBucket) { throw "Could not read BucketName from stack $videoStack" }

    $env:INTEG_API_BASE_URL = $apiBaseUrl.TrimEnd('/')
    $env:INTEG_TABLE_NAME = "StreamMyCourse-Catalog-$Environment"
    $env:INTEG_VIDEO_BUCKET = $videoBucket
    $env:INTEG_REGION = $Region

    if ($CognitoJwt.Trim()) {
        $env:INTEG_COGNITO_JWT = $CognitoJwt.Trim()
    }

    Write-Host "=== Run integration tests ===" -ForegroundColor Cyan
    Write-Host "INTEG_API_BASE_URL=$($env:INTEG_API_BASE_URL)" -ForegroundColor DarkGray
    Write-Host "INTEG_TABLE_NAME=$($env:INTEG_TABLE_NAME)" -ForegroundColor DarkGray
    Write-Host "INTEG_VIDEO_BUCKET=$($env:INTEG_VIDEO_BUCKET)" -ForegroundColor DarkGray
    Write-Host "INTEG_REGION=$($env:INTEG_REGION)" -ForegroundColor DarkGray

    python -m pip install -q -r "$repoRoot\tests\integration\requirements.txt"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $argsList = @('tests/integration', '-q')
    if ($PytestArgs.Trim()) {
        # naive split (good enough for simple switches); pass complex quoting by running python -m pytest manually
        $argsList += $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    }

    python -m pytest @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

