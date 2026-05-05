# One-time (per env): Secrets Manager secret + SSM public PEM for CloudFront signing.
# Usage: .\deploy-cloudfront-keys-stack.ps1 -Environment dev -PrivateKeyPemPath .\cf-private.pem -PublicKeyPemPath .\cf-public.pem

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('dev', 'integ', 'prod')]
    [string]$Environment,

    [Parameter(Mandatory = $true)]
    [string]$PrivateKeyPemPath,

    [Parameter(Mandatory = $true)]
    [string]$PublicKeyPemPath
)

$ErrorActionPreference = 'Stop'
$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { 'eu-west-1' }
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Stack = "StreamMyCourse-CloudFrontKeys-$Environment"
$SsmName = "/streammycourse/$Environment/cloudfront/signing-public-pem"

if (-not (Test-Path -LiteralPath $PrivateKeyPemPath)) {
    throw "Missing private key: $PrivateKeyPemPath"
}
if (-not (Test-Path -LiteralPath $PublicKeyPemPath)) {
    throw "Missing public key: $PublicKeyPemPath"
}

Write-Host "Deploying $Stack"
aws cloudformation deploy `
    --template-file "$Root\infrastructure\templates\cloudfront-keys-stack.yaml" `
    --stack-name $Stack `
    --parameter-overrides "Environment=$Environment" `
    --capabilities CAPABILITY_IAM `
    --region $Region `
    --no-fail-on-empty-changeset

$SecretArn = aws cloudformation describe-stacks `
    --stack-name $Stack `
    --region $Region `
    --query 'Stacks[0].Outputs[?OutputKey==`PrivateKeySecretArn`].OutputValue' `
    --output text

Write-Host "Writing private key to $SecretArn"
aws secretsmanager put-secret-value `
    --secret-id $SecretArn `
    --secret-string "file://$PrivateKeyPemPath" `
    --region $Region

$pubRaw = Get-Content -LiteralPath $PublicKeyPemPath -Raw
Write-Host "Publishing public PEM to SSM: $SsmName"
aws ssm put-parameter `
    --name $SsmName `
    --type String `
    --value $pubRaw `
    --overwrite `
    --region $Region

Write-Host "Done. Set for deploy-backend:"
Write-Host "  CLOUDFRONT_PUBLIC_KEY_SSM_PARAMETER_NAME=$SsmName"
Write-Host "  CLOUDFRONT_PRIVATE_KEY_SECRET_ARN=$SecretArn"
