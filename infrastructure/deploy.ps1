# StreamMyCourse - AWS Deployment Script
param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev",

    [Parameter(Mandatory=$false)]
    [string]$StackName = "",

    [Parameter(Mandatory=$false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory=$false)]
    [ValidateSet("billing", "api", "auth", "video", "edge-hosting", "rds")]
    [string]$Template = "api",

    # api template: name of the rds-stack to import VPC/subnet/SG/secret from.
    # When empty the api-stack deploys in DynamoDB-only mode (no VPC attachment).
    [Parameter(Mandatory=$false)]
    [string]$RdsStackName = "",

    # api template: feature flag that flips between DynamoDB and PostgreSQL adapters.
    [Parameter(Mandatory=$false)]
    [ValidateSet("true", "false", "")]
    [string]$UseRds = "",

    [Parameter(Mandatory=$false)]
    [string]$EmailAddress = "",

    [Parameter(Mandatory=$false)]
    [switch]$Delete,

    [Parameter(Mandatory=$false)]
    [string]$VideoBucketName = "",

    [Parameter(Mandatory=$false)]
    [string]$VideoUrl = "",

    [Parameter(Mandatory=$false)]
    [string]$DefaultMp4Url = "",

    # Web hosting parameters
    [Parameter(Mandatory=$false)]
    [string]$DomainName = "",

    [Parameter(Mandatory=$false)]
    [string]$HostedZoneId = "",

    [Parameter(Mandatory=$false)]
    [string]$CertificateArn = "",

    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "",

    # API CORS (optional; pass when updating allowed origins without editing the template default)
    [Parameter(Mandatory=$false)]
    [string]$CorsAllowOrigin = "",

    [Parameter(Mandatory=$false)]
    [string]$GatewayResponseAllowOrigin = "",

    # edge-hosting: optional comma-separated SANs on the ACM cert (e.g. teacher hostname if not primary)
    [Parameter(Mandatory=$false)]
    [string]$SubjectAlternativeNames = "",

    # edge-hosting: teacher hostname (student uses DomainName)
    [Parameter(Mandatory=$false)]
    [string]$TeacherDomainName = "",

    # edge-hosting: optional ACM primary (defaults to student DomainName)
    [Parameter(Mandatory=$false)]
    [string]$CertPrimaryDomain = "",

    # edge-hosting: set false while legacy CloudFront still owns the same hostnames (see edge-hosting-migration.md)
    [Parameter(Mandatory=$false)]
    [ValidateSet("true", "false")]
    [string]$AttachCloudFrontAliases = "true",

    # auth stack (Cognito)
    [Parameter(Mandatory=$false)]
    [string]$CognitoDomainPrefix = "",

    [Parameter(Mandatory=$false)]
    [string]$StudentCallbackUrls = "",

    [Parameter(Mandatory=$false)]
    [string]$StudentLogoutUrls = "",

    [Parameter(Mandatory=$false)]
    [string]$TeacherCallbackUrls = "",

    [Parameter(Mandatory=$false)]
    [string]$TeacherLogoutUrls = "",

    [Parameter(Mandatory=$false)]
    [string]$GoogleClientId = "",

    [Parameter(Mandatory=$false)]
    [string]$GoogleClientSecret = "",

    # auth stack: optional PostAuthentication Lambda (same RdsStackName as api when USE_RDS=true)
    [Parameter(Mandatory=$false)]
    [ValidateSet("true", "false", "")]
    [string]$EnableUserProfileSync = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoUserProfileSyncCodeS3Bucket = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoUserProfileSyncCodeS3Key = "",

    # api stack: Cognito User Pool ARN for REST authorizer (export from auth stack)
    [Parameter(Mandatory=$false)]
    [string]$CognitoUserPoolArn = "",

    # rds template: PostgreSQL engine version (empty = template default for the region)
    [Parameter(Mandatory=$false)]
    [string]$DbEngineVersion = ""
)

$ErrorActionPreference = "Stop"

# Ensure AWS CLI is on PATH (common Windows install location)
$awsInstallDir = 'C:\Program Files\Amazon\AWSCLIV2'
if (Test-Path (Join-Path $awsInstallDir 'aws.exe')) {
    if ($env:Path -notlike "*${awsInstallDir}*") {
        $env:Path = "${awsInstallDir};${env:Path}"
    }
}

# Web cert and unified edge hosting must be in us-east-1 for CloudFront ACM
$effectiveRegion = $Region
if ($Template -eq "edge-hosting") {
    $effectiveRegion = "us-east-1"
    Write-Host "Note: $Template template requires us-east-1; overriding region" -ForegroundColor Yellow
}

if ($Template -eq "auth") {
    $effectiveRegion = $Region
}

if ($StackName -eq "" -and $Template -eq "rds") {
    $StackName = "StreamMyCourse-Rds-$Environment"
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "StreamMyCourse AWS Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Stack Name:  $StackName" -ForegroundColor Yellow
Write-Host "Region:      $effectiveRegion" -ForegroundColor Yellow
Write-Host "Template:    $Template" -ForegroundColor Yellow
if ($DomainName) { Write-Host "Domain:      $DomainName" -ForegroundColor Yellow }
Write-Host "=========================================" -ForegroundColor Cyan

# Check AWS CLI
try {
    $awsVersion = aws --version 2>&1
    Write-Host "[OK] AWS CLI found: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "[X] AWS CLI not found." -ForegroundColor Red
    exit 1
}

# Check credentials
try {
    $caller = aws sts get-caller-identity --region $Region 2>&1 | ConvertFrom-Json
    Write-Host "[OK] AWS credentials valid" -ForegroundColor Green
    Write-Host "  Account: $($caller.Account)" -ForegroundColor Gray
} catch {
    Write-Host "[X] AWS credentials not configured" -ForegroundColor Red
    exit 1
}

$templatePath = "$PSScriptRoot\templates\$Template-stack.yaml"
if ($Template -eq "billing") {
    $templatePath = "$PSScriptRoot\templates\billing-alarm.yaml"
}
if (-not (Test-Path $templatePath)) {
    Write-Host "[X] Template not found: $templatePath" -ForegroundColor Red
    exit 1
}

if ($Delete) {
    Write-Host "`nDeleting stack $StackName..." -ForegroundColor Red
    aws cloudformation delete-stack --stack-name $StackName --region $effectiveRegion
    aws cloudformation wait stack-delete-complete --stack-name $StackName --region $effectiveRegion
    Write-Host "[OK] Stack deleted" -ForegroundColor Green
    exit 0
}

Write-Host "`nDeploying stack $StackName..." -ForegroundColor Cyan

# Package Lambda code if deploying API stack
if ($Template -eq "api") {
    $lambdaSourceDir = "$PSScriptRoot\lambda\catalog"
    $artifactBucket = "streammycourse-artifacts-$($caller.Account)-$Region"
    $gitSha = (& git -C $PSScriptRoot rev-parse HEAD 2>$null)
    if (-not $gitSha) { $gitSha = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString() }
    $gitSha = $gitSha.Trim()
    $short = if ($gitSha.Length -ge 12) { $gitSha.Substring(0, 12) } else { $gitSha }
    # Include content hash to force Lambda code updates even without a new git commit.
    $lambdaKey = ""

    # Create artifacts bucket if it doesn't exist
    try {
        aws s3api head-bucket --bucket $artifactBucket --region $Region 2>&1 | Out-Null
    } catch {
        Write-Host "Creating artifacts bucket: $artifactBucket" -ForegroundColor Yellow
        aws s3 mb "s3://$artifactBucket" --region $Region
        aws s3api put-bucket-versioning --bucket $artifactBucket --versioning-configuration Status=Enabled --region $Region
    }

    # Zip Lambda code
    $tempZip = "$env:TEMP\catalog-$Environment.zip"
    if (Test-Path $tempZip) { Remove-Item $tempZip -Force }

    # Ensure we never ship local bytecode caches (can cause stale code in Lambda)
    Get-ChildItem -Path $lambdaSourceDir -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq '__pycache__' } |
        ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
    Get-ChildItem -Path $lambdaSourceDir -Recurse -Include *.pyc -File -Force -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue }

    # Vendor runtime deps (psycopg2-binary) into a build-staging dir so
    # Compress-Archive picks them up alongside the source tree. Avoids
    # polluting the checkout with _vendor/ between runs.
    $buildDir = Join-Path $env:TEMP "catalog-build-$Environment-$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
    if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
    New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
    Copy-Item -Path "$lambdaSourceDir\*" -Destination $buildDir -Recurse -Force

    $reqFile = Join-Path $lambdaSourceDir "requirements.txt"
    if (Test-Path $reqFile) {
        Write-Host "Installing Lambda runtime deps into $buildDir\_vendor" -ForegroundColor Yellow
        & python -m pip install `
            --quiet `
            --platform manylinux2014_x86_64 `
            --only-binary=:all: `
            --python-version 3.11 `
            --implementation cp `
            -r $reqFile `
            -t (Join-Path $buildDir "_vendor")
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[X] pip install failed; cannot package Lambda" -ForegroundColor Red
            Remove-Item $buildDir -Recurse -Force
            exit 1
        }
    }

    Compress-Archive -Path "$buildDir\*" -DestinationPath $tempZip -Force
    Remove-Item $buildDir -Recurse -Force

    # Upload to S3
    $zipHash = (Get-FileHash -Path $tempZip -Algorithm SHA256).Hash.Substring(0, 12).ToLower()
    $lambdaKey = "catalog-$Environment-$short-$zipHash.zip"
    Write-Host "Uploading Lambda code to s3://$artifactBucket/$lambdaKey" -ForegroundColor Yellow
    aws s3 cp $tempZip "s3://$artifactBucket/$lambdaKey" --region $Region
    Remove-Item $tempZip -Force
}

# Schema-applier Lambda zip for RDS stack (same layout as CI deploy-rds-dev).
$rdsArtifactBucket = ""
$rdsSchemaKey = ""
if ($Template -eq "rds") {
    $rdsArtifactBucket = "streammycourse-artifacts-$($caller.Account)-$Region"
    try {
        aws s3api head-bucket --bucket $rdsArtifactBucket --region $Region 2>&1 | Out-Null
    } catch {
        Write-Host "Creating artifacts bucket: $rdsArtifactBucket" -ForegroundColor Yellow
        aws s3 mb "s3://$rdsArtifactBucket" --region $Region
        aws s3api put-bucket-versioning --bucket $rdsArtifactBucket --versioning-configuration Status=Enabled --region $Region
    }

    $gitSha = (& git -C $PSScriptRoot rev-parse HEAD 2>$null)
    if (-not $gitSha) { $gitSha = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString() }
    $gitSha = $gitSha.Trim()
    $short = if ($gitSha.Length -ge 12) { $gitSha.Substring(0, 12) } else { $gitSha }
    $rdsSchemaKey = "rds-schema-apply-$Environment-$short.zip"

    $schemaHandler = "$PSScriptRoot\lambda\rds_schema_apply\index.py"
    $schemaSql = "$PSScriptRoot\database\migrations\001_initial_schema.sql"
    if (-not (Test-Path $schemaHandler)) {
        Write-Host "[X] Missing schema applier: $schemaHandler" -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path $schemaSql)) {
        Write-Host "[X] Missing migration SQL: $schemaSql" -ForegroundColor Red
        exit 1
    }

    $pkgRoot = Join-Path $env:TEMP "rds-schema-pkg-$Environment-$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
    $pkgDir = $pkgRoot
    New-Item -ItemType Directory -Path $pkgDir -Force | Out-Null
    Copy-Item -Path $schemaHandler -Destination (Join-Path $pkgDir "index.py") -Force
    Copy-Item -Path $schemaSql -Destination (Join-Path $pkgDir "schema.sql") -Force

    Write-Host "Installing psycopg2-binary (Linux x86_64) into schema-applier bundle" -ForegroundColor Yellow
    & python -m pip install `
        --quiet `
        psycopg2-binary==2.9.9 `
        --platform manylinux2014_x86_64 `
        --only-binary=:all: `
        --python-version 3.11 `
        --implementation cp `
        -t $pkgDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] pip install failed for schema applier" -ForegroundColor Red
        Remove-Item $pkgRoot -Recurse -Force -ErrorAction SilentlyContinue
        exit 1
    }

    $tempZip = "$env:TEMP\rds-schema-$Environment.zip"
    if (Test-Path $tempZip) { Remove-Item $tempZip -Force }
    Compress-Archive -Path "$pkgDir\*" -DestinationPath $tempZip -Force
    Remove-Item $pkgRoot -Recurse -Force

    Write-Host "Uploading schema-applier to s3://$rdsArtifactBucket/$rdsSchemaKey" -ForegroundColor Yellow
    aws s3 cp $tempZip "s3://$rdsArtifactBucket/$rdsSchemaKey" --region $Region
    Remove-Item $tempZip -Force
}

# CloudFront invalidation Lambda zip for video stack (runtime boto3 only; index.py in bundle root).
$videoArtifactBucket = ""
$videoInvalidationKey = ""
if ($Template -eq "video") {
    $videoArtifactBucket = "streammycourse-artifacts-$($caller.Account)-$Region"
    try {
        aws s3api head-bucket --bucket $videoArtifactBucket --region $Region 2>&1 | Out-Null
    } catch {
        Write-Host "Creating artifacts bucket: $videoArtifactBucket" -ForegroundColor Yellow
        aws s3 mb "s3://$videoArtifactBucket" --region $Region
        aws s3api put-bucket-versioning --bucket $videoArtifactBucket --versioning-configuration Status=Enabled --region $Region
    }
    $gitSha = (& git -C $PSScriptRoot rev-parse HEAD 2>$null)
    if (-not $gitSha) { $gitSha = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString() }
    $gitSha = $gitSha.Trim()
    $short = if ($gitSha.Length -ge 12) { $gitSha.Substring(0, 12) } else { $gitSha }
    $videoInvalidationKey = "cf-invalidate-$Environment-$short.zip"
    $invDir = "$PSScriptRoot\lambda\cloudfront_invalidation"
    $invHandler = Join-Path $invDir "index.py"
    if (-not (Test-Path $invHandler)) {
        Write-Host "[X] Missing CloudFront invalidation Lambda: $invHandler" -ForegroundColor Red
        exit 1
    }
    $tempZip = "$env:TEMP\cf-invalidate-$Environment.zip"
    if (Test-Path $tempZip) { Remove-Item $tempZip -Force }
    Push-Location $invDir
    try {
        Compress-Archive -Path "index.py" -DestinationPath $tempZip -Force
    } finally {
        Pop-Location
    }
    Write-Host "Uploading CloudFront invalidation bundle to s3://$videoArtifactBucket/$videoInvalidationKey" -ForegroundColor Yellow
    aws s3 cp $tempZip "s3://$videoArtifactBucket/$videoInvalidationKey" --region $Region
    Remove-Item $tempZip -Force
}

$paramOverrides = "Environment=$Environment"
if ($Template -eq "billing") {
    $paramOverrides = "ThresholdAmount=10"
    if ($EmailAddress -ne "") {
        $paramOverrides += ",EmailAddress=$EmailAddress"
    }
}
# API parameter overrides are passed as separate argv tokens (see $cfDeployArgs below)
if ($Template -eq "auth") {
    if ($CognitoDomainPrefix -eq "") {
        Write-Host "[X] CognitoDomainPrefix is required for auth template (globally unique, e.g. streammycourse-auth-dev)" -ForegroundColor Red
        exit 1
    }
    if ($GoogleClientId -eq "" -or $GoogleClientSecret -eq "") {
        Write-Host "[X] GoogleClientId and GoogleClientSecret are required for auth template (Google-federation-only stack)." -ForegroundColor Red
        exit 1
    }
}

if ($Template -eq "edge-hosting") {
    if ($DomainName -eq "") {
        Write-Host "[X] DomainName is required for edge-hosting (student site hostname)" -ForegroundColor Red
        exit 1
    }
    if ($TeacherDomainName -eq "") {
        Write-Host "[X] TeacherDomainName is required for edge-hosting (teacher site hostname)" -ForegroundColor Red
        exit 1
    }
    if ($HostedZoneId -eq "") {
        Write-Host "[X] HostedZoneId is required for edge-hosting template" -ForegroundColor Red
        exit 1
    }
}

$capabilities = @('CAPABILITY_IAM')
# api + rds + auth + video templates create IAM roles with explicit RoleName (named IAM resources).
if ($Template -eq "api" -or $Template -eq "rds" -or $Template -eq "auth" -or $Template -eq "video") {
    $capabilities = @('CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM')
}

# AWS CLI expects multiple Key=Value tokens after --parameter-overrides (not one comma-joined string; ARNs contain colons)
$cfDeployArgs = @(
    'cloudformation', 'deploy',
    '--template-file', $templatePath,
    '--stack-name', $StackName,
    '--region', $effectiveRegion,
    '--no-fail-on-empty-changeset'
)
$cfDeployArgs += '--capabilities'
$cfDeployArgs += $capabilities
if ($Template -eq "edge-hosting") {
    $certPrimary = if ($CertPrimaryDomain -ne "") { $CertPrimaryDomain } else { $DomainName }
    $edgeOverrides = @(
        "Environment=$Environment",
        "HostedZoneId=$HostedZoneId",
        "CertPrimaryDomain=$certPrimary",
        "StudentDomainName=$DomainName",
        "TeacherDomainName=$TeacherDomainName",
        "PriceClass=PriceClass_100",
        "AttachCloudFrontAliases=$AttachCloudFrontAliases"
    )
    if ($SubjectAlternativeNames -ne "") {
        $edgeOverrides += "SubjectAlternativeNames=$SubjectAlternativeNames"
    }
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $edgeOverrides
} elseif ($Template -eq "auth") {
    $authOverrides = @(
        "Environment=$Environment",
        "CognitoDomainPrefix=$CognitoDomainPrefix"
    )
    if ($StudentCallbackUrls -ne "") {
        $authOverrides += "StudentCallbackUrls=$StudentCallbackUrls"
    }
    if ($StudentLogoutUrls -ne "") {
        $authOverrides += "StudentLogoutUrls=$StudentLogoutUrls"
    }
    if ($TeacherCallbackUrls -ne "") {
        $authOverrides += "TeacherCallbackUrls=$TeacherCallbackUrls"
    }
    if ($TeacherLogoutUrls -ne "") {
        $authOverrides += "TeacherLogoutUrls=$TeacherLogoutUrls"
    }
    $authOverrides += "GoogleClientId=$GoogleClientId"
    $authOverrides += "GoogleClientSecret=$GoogleClientSecret"
    if ($RdsStackName -ne "") {
        $authOverrides += "RdsStackName=$RdsStackName"
    }
    if ($EnableUserProfileSync -ne "") {
        $authOverrides += "EnableUserProfileSync=$EnableUserProfileSync"
    }
    if ($CognitoUserProfileSyncCodeS3Bucket -ne "") {
        $authOverrides += "CognitoUserProfileSyncCodeS3Bucket=$CognitoUserProfileSyncCodeS3Bucket"
    }
    if ($CognitoUserProfileSyncCodeS3Key -ne "") {
        $authOverrides += "CognitoUserProfileSyncCodeS3Key=$CognitoUserProfileSyncCodeS3Key"
    }
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $authOverrides
} elseif ($Template -eq "api") {
    $apiOverrides = @(
        "Environment=$Environment",
        "LambdaCodeS3Bucket=$artifactBucket",
        "LambdaCodeS3Key=$lambdaKey"
    )
    if ($VideoBucketName -ne "") {
        $apiOverrides += "VideoBucketName=$VideoBucketName"
    }
    if ($VideoUrl -ne "") {
        $apiOverrides += "VideoUrl=$VideoUrl"
    }
    if ($DefaultMp4Url -ne "") {
        $apiOverrides += "DefaultMp4Url=$DefaultMp4Url"
    }
    if ($CorsAllowOrigin -ne "") {
        $apiOverrides += "CorsAllowOrigin=$CorsAllowOrigin"
    }
    if ($GatewayResponseAllowOrigin -ne "") {
        $apiOverrides += "GatewayResponseAllowOrigin=$GatewayResponseAllowOrigin"
    }
    if ($CognitoUserPoolArn -ne "") {
        $apiOverrides += "CognitoUserPoolArn=$CognitoUserPoolArn"
    }
    if ($RdsStackName -ne "") {
        $apiOverrides += "RdsStackName=$RdsStackName"
    }
    if ($UseRds -ne "") {
        $apiOverrides += "UseRds=$UseRds"
    }
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $apiOverrides
} elseif ($Template -eq "rds") {
    $rdsOverrides = @(
        "Environment=$Environment",
        "SchemaApplierCodeS3Bucket=$rdsArtifactBucket",
        "SchemaApplierCodeS3Key=$rdsSchemaKey"
    )
    if ($DbEngineVersion -ne "") {
        $rdsOverrides += "DbEngineVersion=$DbEngineVersion"
    }
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $rdsOverrides
} elseif ($Template -eq "video") {
    $videoOverrides = @(
        "Environment=$Environment",
        "InvalidationLambdaCodeS3Bucket=$videoArtifactBucket",
        "InvalidationLambdaCodeS3Key=$videoInvalidationKey"
    )
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $videoOverrides
} else {
    $cfDeployArgs += '--parameter-overrides', $paramOverrides
}

& aws @cfDeployArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Stack deployment successful!" -ForegroundColor Green

    if ($Template -eq "rds") {
        Write-Host "Waiting for RDS instance streammycourse-$Environment to become available..." -ForegroundColor Yellow
        aws rds wait db-instance-available --db-instance-identifier "streammycourse-$Environment" --region $effectiveRegion
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[X] Timed out or failed waiting for RDS instance" -ForegroundColor Red
            exit 1
        }
    }

    Write-Host "`nStack Outputs:" -ForegroundColor Cyan
    aws cloudformation describe-stacks --stack-name $StackName --region $effectiveRegion --query 'Stacks[0].Outputs' --output table
} else {
    Write-Host "`n[X] Deployment failed" -ForegroundColor Red
    aws cloudformation describe-stack-events --stack-name $StackName --region $effectiveRegion --query 'StackEvents[?ResourceStatus==''CREATE_FAILED''].[LogicalResourceId,ResourceStatusReason]' --output table
}
