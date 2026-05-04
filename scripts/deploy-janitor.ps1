# Deploy the Artifact Janitor Lambda for scheduled S3 cleanup.
# Usage: deploy-janitor.ps1 [dev|integ|prod] [keepCount] [dryRun]
param(
    [string]$Environment = "dev",
    [int]$KeepCount = 2,
    [string]$DryRun = "false"
)

$Region = $env:AWS_REGION
if (-not $Region) { $Region = "eu-west-1" }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$TemplateDir = Join-Path $Root "infrastructure\templates"
$LambdaDir = Join-Path $Root "infrastructure\lambda\artifact_janitor"

$Account = (aws sts get-caller-identity --query Account --output text --region $Region).Trim()
$ArtifactBucket = "streammycourse-artifacts-${Account}-${Region}"
$StackName = "StreamMyCourse-ArtifactJanitor-${Environment}"
$FunctionName = "StreamMyCourse-ArtifactJanitor-${Environment}"

Write-Host "=== Deploying Artifact Janitor ===" -ForegroundColor Cyan
Write-Host "Environment: $Environment"
Write-Host "Artifact bucket: $ArtifactBucket"
Write-Host "Keep count: $KeepCount"
Write-Host "Dry run: $DryRun"
Write-Host ""

# Create temp zip
$ZipFile = [System.IO.Path]::GetTempFileName() + ".zip"
Write-Host "Packaging Lambda code..." -ForegroundColor Yellow

# Use Compress-Archive for cross-platform compatibility
$TempDir = [System.IO.Path]::GetTempFileName()
Remove-Item $TempDir
New-Item -ItemType Directory -Path $TempDir | Out-Null
Copy-Item "$LambdaDir\*" $TempDir -Recurse
Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipFile -Force
Remove-Item $TempDir -Recurse

try {
    # Check if stack exists
    $StackExists = $false
    try {
        aws cloudformation describe-stacks --stack-name $StackName --region $Region 2>$null | Out-Null
        $StackExists = $true
    } catch {}

    if (-not $StackExists) {
        Write-Host "Stack does not exist. Creating initial stack..." -ForegroundColor Yellow
        aws cloudformation deploy `
            --template-file "$TemplateDir\artifact-janitor-stack.yaml" `
            --stack-name $StackName `
            --capabilities CAPABILITY_IAM `
            --region $Region `
            --no-fail-on-empty-changeset `
            --parameter-overrides `
                "Environment=$Environment" `
                "ArtifactBucketName=$ArtifactBucket" `
                "KeepCount=$KeepCount" `
                "DryRun=$DryRun"
    }

    # Update Lambda code
    Write-Host "Updating Lambda function code..." -ForegroundColor Yellow
    aws lambda update-function-code `
        --function-name $FunctionName `
        --zip-file "fileb://$ZipFile" `
        --region $Region `
        --publish

    Write-Host ""
    Write-Host "Updating stack parameters..." -ForegroundColor Yellow
    aws cloudformation deploy `
        --template-file "$TemplateDir\artifact-janitor-stack.yaml" `
        --stack-name $StackName `
        --capabilities CAPABILITY_IAM `
        --region $Region `
        --no-fail-on-empty-changeset `
        --parameter-overrides `
            "Environment=$Environment" `
            "ArtifactBucketName=$ArtifactBucket" `
            "KeepCount=$KeepCount" `
            "DryRun=$DryRun"

    Write-Host ""
    Write-Host "=== Deployment Complete ===" -ForegroundColor Green
    Write-Host "Stack: $StackName"
    Write-Host "Function: $FunctionName"
    Write-Host "Schedule: Daily (rate: 1 day)"
    Write-Host ""
    Write-Host "To trigger manually:"
    Write-Host "  aws lambda invoke --function-name $FunctionName --region $Region --payload '{}' response.json"
    Write-Host ""
    Write-Host "To view logs:"
    Write-Host "  aws logs tail /aws/lambda/$FunctionName --region $Region --follow"
} finally {
    # Cleanup
    if (Test-Path $ZipFile) {
        Remove-Item $ZipFile -Force
    }
}
