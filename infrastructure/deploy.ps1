# StreamMyCourse - AWS Deployment Script
param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "prod",

    [Parameter(Mandatory=$false)]
    [string]$StackName = "",

    [Parameter(Mandatory=$false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory=$false)]
    [ValidateSet("billing", "api", "auth", "video", "edge-hosting")]
    [string]$Template = "api",

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

    # auth stack: optional PostAuthentication Lambda (DSQL profile sync when DsqlEndpoint is set)
    [Parameter(Mandatory=$false)]
    [ValidateSet("true", "false", "")]
    [string]$EnableUserProfileSync = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoUserProfileSyncCodeS3Bucket = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoUserProfileSyncCodeS3Key = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoPreSignUpCodeS3Bucket = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoPreSignUpCodeS3Key = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoCustomEmailSenderCodeS3Bucket = "",

    [Parameter(Mandatory=$false)]
    [string]$CognitoCustomEmailSenderCodeS3Key = "",

    [Parameter(Mandatory=$false)]
    [string]$ZohoSmtpSecretArn = "",

    # api stack: Cognito User Pool ARN + client id(s) for REST authorizer (export from auth stack)
    [Parameter(Mandatory=$true)]
    [string]$CognitoUserPoolArn,

    [Parameter(Mandatory=$true)]
    [string]$CognitoClientId,

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

function Get-DsqlStackOutputs {
    param(
        [string]$Env,
        [string]$Reg
    )
    $dsqlStack = "StreamMyCourse-Dsql-$Env"
    try {
        $endpoint = aws cloudformation describe-stacks --stack-name $dsqlStack --region $Reg `
            --query "Stacks[0].Outputs[?OutputKey=='Endpoint'].OutputValue" --output text 2>$null
        $clusterArn = aws cloudformation describe-stacks --stack-name $dsqlStack --region $Reg `
            --query "Stacks[0].Outputs[?OutputKey=='ResourceArn'].OutputValue" --output text 2>$null
        if ($endpoint -and $endpoint -ne "None" -and $clusterArn -and $clusterArn -ne "None") {
            return @{ Endpoint = $endpoint.Trim(); ClusterArn = $clusterArn.Trim() }
        }
    } catch {
        return $null
    }
    return $null
}

$dsqlOutputs = $null
if ($Template -eq "api" -or $Template -eq "auth") {
    $dsqlOutputs = Get-DsqlStackOutputs -Env $Environment -Reg $Region
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
    $authorizerSourceDir = "$PSScriptRoot\lambda\catalog_token_authorizer"
    $artifactBucket = "streammycourse-artifacts-$($caller.Account)-$Region"
    $gitSha = (& git -C $PSScriptRoot rev-parse HEAD 2>$null)
    if (-not $gitSha) { $gitSha = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString() }
    $gitSha = $gitSha.Trim()
    $short = if ($gitSha.Length -ge 12) { $gitSha.Substring(0, 12) } else { $gitSha }
    # Include content hash to force Lambda code updates even without a new git commit.
    $lambdaKey = ""
    $tokenAuthorizerKey = ""

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

    # Vendor runtime deps (psycopg2-binary) into a temp build dir so
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

    # --- Package TOKEN authorizer Lambda (outside VPC) ----------------------------
    if (-not (Test-Path $authorizerSourceDir)) {
        Write-Host "[X] Token authorizer source directory missing: $authorizerSourceDir" -ForegroundColor Red
        exit 1
    }

    $authZip = "$env:TEMP\catalog-token-authorizer-$Environment.zip"
    if (Test-Path $authZip) { Remove-Item $authZip -Force }

    $authBuildDir = Join-Path $env:TEMP "catalog-token-authorizer-build-$Environment-$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
    if (Test-Path $authBuildDir) { Remove-Item $authBuildDir -Recurse -Force }
    New-Item -ItemType Directory -Path $authBuildDir -Force | Out-Null
    Copy-Item -Path "$authorizerSourceDir\*" -Destination $authBuildDir -Recurse -Force

    $authReqFile = Join-Path $authorizerSourceDir "requirements.txt"
    if (Test-Path $authReqFile) {
        Write-Host "Installing TOKEN authorizer runtime deps into $authBuildDir\_vendor" -ForegroundColor Yellow
        & python -m pip install `
            --quiet `
            --platform manylinux2014_x86_64 `
            --only-binary=:all: `
            --python-version 3.11 `
            --implementation cp `
            -r $authReqFile `
            -t (Join-Path $authBuildDir "_vendor")
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[X] pip install failed; cannot package TOKEN authorizer Lambda" -ForegroundColor Red
            Remove-Item $authBuildDir -Recurse -Force
            exit 1
        }
    }

    Compress-Archive -Path "$authBuildDir\*" -DestinationPath $authZip -Force
    Remove-Item $authBuildDir -Recurse -Force

    $authZipHash = (Get-FileHash -Path $authZip -Algorithm SHA256).Hash.Substring(0, 12).ToLower()
    $tokenAuthorizerKey = "catalog-token-authorizer-$Environment-$short-$authZipHash.zip"
    Write-Host "Uploading TOKEN authorizer code to s3://$artifactBucket/$tokenAuthorizerKey" -ForegroundColor Yellow
    aws s3 cp $authZip "s3://$artifactBucket/$tokenAuthorizerKey" --region $Region
    Remove-Item $authZip -Force
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
        Write-Host "[X] CognitoDomainPrefix is required for auth template (globally unique, e.g. streammycourse-auth-prod)" -ForegroundColor Red
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
# api + auth + video templates create IAM roles with explicit RoleName (named IAM resources).
if ($Template -eq "api" -or $Template -eq "auth" -or $Template -eq "video") {
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
    # Ensure local Vite OAuth redirects exist (including when callback env vars are empty).
    if (-not $StudentCallbackUrls.Contains('http://localhost:5173/')) {
        $StudentCallbackUrls = $(if ([string]::IsNullOrWhiteSpace($StudentCallbackUrls)) { 'http://localhost:5173/' } else { "$StudentCallbackUrls,http://localhost:5173/" })
    }
    if (-not $StudentCallbackUrls.Contains('http://127.0.0.1:5173/')) {
        $StudentCallbackUrls = $(if ([string]::IsNullOrWhiteSpace($StudentCallbackUrls)) { 'http://127.0.0.1:5173/' } else { "$StudentCallbackUrls,http://127.0.0.1:5173/" })
    }
    if (-not $StudentLogoutUrls.Contains('http://localhost:5173/')) {
        $StudentLogoutUrls = $(if ([string]::IsNullOrWhiteSpace($StudentLogoutUrls)) { 'http://localhost:5173/' } else { "$StudentLogoutUrls,http://localhost:5173/" })
    }
    if (-not $StudentLogoutUrls.Contains('http://127.0.0.1:5173/')) {
        $StudentLogoutUrls = $(if ([string]::IsNullOrWhiteSpace($StudentLogoutUrls)) { 'http://127.0.0.1:5173/' } else { "$StudentLogoutUrls,http://127.0.0.1:5173/" })
    }
    if (-not $TeacherCallbackUrls.Contains('http://localhost:5174/')) {
        $TeacherCallbackUrls = $(if ([string]::IsNullOrWhiteSpace($TeacherCallbackUrls)) { 'http://localhost:5174/' } else { "$TeacherCallbackUrls,http://localhost:5174/" })
    }
    if (-not $TeacherCallbackUrls.Contains('http://127.0.0.1:5174/')) {
        $TeacherCallbackUrls = $(if ([string]::IsNullOrWhiteSpace($TeacherCallbackUrls)) { 'http://127.0.0.1:5174/' } else { "$TeacherCallbackUrls,http://127.0.0.1:5174/" })
    }
    if (-not $TeacherLogoutUrls.Contains('http://localhost:5174/')) {
        $TeacherLogoutUrls = $(if ([string]::IsNullOrWhiteSpace($TeacherLogoutUrls)) { 'http://localhost:5174/' } else { "$TeacherLogoutUrls,http://localhost:5174/" })
    }
    if (-not $TeacherLogoutUrls.Contains('http://127.0.0.1:5174/')) {
        $TeacherLogoutUrls = $(if ([string]::IsNullOrWhiteSpace($TeacherLogoutUrls)) { 'http://127.0.0.1:5174/' } else { "$TeacherLogoutUrls,http://127.0.0.1:5174/" })
    }
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
    if ($null -ne $dsqlOutputs) {
        $authOverrides += "DsqlEndpoint=$($dsqlOutputs.Endpoint)"
        $authOverrides += "DsqlClusterArn=$($dsqlOutputs.ClusterArn)"
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
    if ($CognitoPreSignUpCodeS3Bucket -ne "") {
        $authOverrides += "CognitoPreSignUpCodeS3Bucket=$CognitoPreSignUpCodeS3Bucket"
    }
    if ($CognitoPreSignUpCodeS3Key -ne "") {
        $authOverrides += "CognitoPreSignUpCodeS3Key=$CognitoPreSignUpCodeS3Key"
    }
    if ($CognitoCustomEmailSenderCodeS3Bucket -ne "") {
        $authOverrides += "CognitoCustomEmailSenderCodeS3Bucket=$CognitoCustomEmailSenderCodeS3Bucket"
    }
    if ($CognitoCustomEmailSenderCodeS3Key -ne "") {
        $authOverrides += "CognitoCustomEmailSenderCodeS3Key=$CognitoCustomEmailSenderCodeS3Key"
    }
    if ($ZohoSmtpSecretArn -ne "") {
        $authOverrides += "ZohoSmtpSecretArn=$ZohoSmtpSecretArn"
    }
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $authOverrides
} elseif ($Template -eq "api") {
    if ($null -eq $dsqlOutputs) {
        Write-Host "[X] StreamMyCourse-Dsql-$Environment must exist (Endpoint + ResourceArn outputs) before api deploy." -ForegroundColor Red
        exit 1
    }
    # api-stack.yaml can exceed CloudFormation's 51,200-byte inline template limit.
    $cfDeployArgs += '--s3-bucket', $artifactBucket
    $cfDeployArgs += '--s3-prefix', "cf-api-template/$Environment/"
    $apiOverrides = @(
        "Environment=$Environment",
        "LambdaCodeS3Bucket=$artifactBucket",
        "LambdaCodeS3Key=$lambdaKey",
        "TokenAuthorizerCodeS3Key=$tokenAuthorizerKey",
        "DsqlEndpoint=$($dsqlOutputs.Endpoint)",
        "DsqlClusterArn=$($dsqlOutputs.ClusterArn)"
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
    $apiOverrides += "CognitoUserPoolArn=$CognitoUserPoolArn"
    $apiOverrides += "CognitoClientId=$CognitoClientId"
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $apiOverrides
} elseif ($Template -eq "video") {
    $videoCors = 'https://researchspectrum.org,https://teach.researchspectrum.org,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174'
    $videoOverrides = @(
        "Environment=$Environment",
        "InvalidationLambdaCodeS3Bucket=$videoArtifactBucket",
        "InvalidationLambdaCodeS3Key=$videoInvalidationKey",
        "CorsAllowedOrigins=$videoCors"
    )
    $cfDeployArgs += '--parameter-overrides'
    $cfDeployArgs += $videoOverrides
} else {
    $cfDeployArgs += '--parameter-overrides', $paramOverrides
}

& aws @cfDeployArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Stack deployment successful!" -ForegroundColor Green

    Write-Host "`nStack Outputs:" -ForegroundColor Cyan
    aws cloudformation describe-stacks --stack-name $StackName --region $effectiveRegion --query 'Stacks[0].Outputs' --output table
} else {
    Write-Host "`n[X] Deployment failed" -ForegroundColor Red
    aws cloudformation describe-stack-events --stack-name $StackName --region $effectiveRegion --query 'StackEvents[?ResourceStatus==''CREATE_FAILED''].[LogicalResourceId,ResourceStatusReason]' --output table
}
