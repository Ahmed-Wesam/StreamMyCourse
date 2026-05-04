#!/usr/bin/env bash
# Deploy video (S3) + API (Lambda, API Gateway, DynamoDB) for one environment.
# Mirrors infrastructure/deploy-environment.ps1 for use in CI (Linux) or locally (Git Bash / WSL).
set -euo pipefail

ENV="${1:?Usage: deploy-backend.sh <dev|integ|prod>}"
case "$ENV" in
dev | integ | prod) ;;
*)
  echo "Environment must be dev, integ, or prod, got: $ENV" >&2
  exit 1
  ;;
esac

REGION="${AWS_REGION:-eu-west-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT/infrastructure/templates"
LAMBDA_DIR="$ROOT/infrastructure/lambda/catalog"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
ARTIFACT_BUCKET="streammycourse-artifacts-${ACCOUNT}-${REGION}"

# CloudFormation only updates Lambda when S3Key *parameter* changes. Same key + new zip bytes = empty changeset.
SUFFIX="${LAMBDA_CODE_SUFFIX:-}"
if [[ -z "$SUFFIX" ]] && [[ -n "${GITHUB_SHA:-}" ]]; then
  SUFFIX="${GITHUB_SHA:0:12}"
fi
if [[ -z "$SUFFIX" ]]; then
  if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
    SUFFIX="$(git -C "$ROOT" rev-parse HEAD | cut -c1-12)"
  else
    SUFFIX="$(date +%s)"
  fi
fi
ZIP_KEY="catalog-${ENV}-${SUFFIX}.zip"

if ! aws s3api head-bucket --bucket "$ARTIFACT_BUCKET" --region "$REGION" 2>/dev/null; then
  echo "Creating artifacts bucket: $ARTIFACT_BUCKET"
  aws s3 mb "s3://${ARTIFACT_BUCKET}" --region "$REGION"
  aws s3api put-bucket-versioning \
    --bucket "$ARTIFACT_BUCKET" \
    --versioning-configuration Status=Enabled \
    --region "$REGION"
fi

# Do not use mktemp's empty file as the zip target — zip(1) treats it as a corrupt archive and exits 3.
ZIP="/tmp/catalog-lambda-${ENV}-$$.zip"
BUILD_DIR="/tmp/catalog-build-${ENV}-$$"
trap 'rm -f "$ZIP"; rm -rf "$BUILD_DIR"' EXIT
[[ -d "$LAMBDA_DIR" ]] || {
  echo "Lambda source directory missing: $LAMBDA_DIR" >&2
  exit 1
}

# Stage sources into a build dir so pip install -t _vendor does not contaminate the
# checkout. This also keeps the zip reproducible — no stray _vendor/ from a prior run.
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
# Copy *everything* except any local _vendor/ or __pycache__/ directories.
( cd "$LAMBDA_DIR" && \
  find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
    | xargs -0 -I{} cp --parents '{}' "$BUILD_DIR" )

# Vendor runtime deps (psycopg2-binary for RDS access). --platform + --only-binary
# pins the wheel to Lambda's Amazon Linux x86_64 runtime even when building on
# macOS/Windows. Lambda provides boto3; we do NOT package it.
REQ_FILE="$LAMBDA_DIR/requirements.txt"
if [[ -f "$REQ_FILE" ]]; then
  echo "Installing Lambda runtime deps into $BUILD_DIR/_vendor"
  pip install \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    -r "$REQ_FILE" \
    -t "$BUILD_DIR/_vendor"
fi

( cd "$BUILD_DIR" && zip -rq "$ZIP" . )
echo "Uploading Lambda s3://${ARTIFACT_BUCKET}/${ZIP_KEY}"
aws s3 cp "$ZIP" "s3://${ARTIFACT_BUCKET}/${ZIP_KEY}" --region "$REGION"

INV_ZIP="/tmp/cf-invalidate-${ENV}-$$.zip"
INV_KEY="cf-invalidate-${ENV}-${SUFFIX}.zip"
CF_INV_DIR="${ROOT}/infrastructure/lambda/cloudfront_invalidation"
if [[ ! -f "${CF_INV_DIR}/index.py" ]]; then
  echo "Missing CloudFront invalidation Lambda: ${CF_INV_DIR}/index.py" >&2
  exit 1
fi
( cd "$CF_INV_DIR" && zip -jq "$INV_ZIP" index.py )
echo "Uploading CloudFront invalidation bundle s3://${ARTIFACT_BUCKET}/${INV_KEY}"
aws s3 cp "$INV_ZIP" "s3://${ARTIFACT_BUCKET}/${INV_KEY}" --region "$REGION"
rm -f "$INV_ZIP"

VIDEO_STACK="StreamMyCourse-Video-${ENV}"
echo "Deploying video stack: $VIDEO_STACK"
aws cloudformation deploy \
  --template-file "$TEMPLATE_DIR/video-stack.yaml" \
  --stack-name "$VIDEO_STACK" \
  --parameter-overrides \
    "Environment=${ENV}" \
    "InvalidationLambdaCodeS3Bucket=${ARTIFACT_BUCKET}" \
    "InvalidationLambdaCodeS3Key=${INV_KEY}" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

VIDEO_BUCKET="$(aws cloudformation describe-stacks \
  --stack-name "$VIDEO_STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)"
BUCKET_URL="$(aws cloudformation describe-stacks \
  --stack-name "$VIDEO_STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketURL`].OutputValue' \
  --output text)"

if [[ -z "$VIDEO_BUCKET" || -z "$BUCKET_URL" ]]; then
  echo "Failed to read video stack outputs (BucketName / BucketURL)" >&2
  exit 1
fi

case "$ENV" in
prod)
  API_STACK="StreamMyCourse-Api-prod"
  CORS="https://app.streammycourse.click,https://teach.streammycourse.click,http://localhost:5173,http://localhost:5174"
  GW_ALLOW="https://app.streammycourse.click"
  ;;
integ)
  API_STACK="StreamMyCourse-Api-integ"
  # Integ: explicit origins (no wildcard) for API + gateway error CORS.
  CORS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
  GW_ALLOW="http://localhost:5173"
  ;;
dev)
  API_STACK="streammycourse-api"
  CORS="https://dev.streammycourse.click,https://teach.dev.streammycourse.click,http://localhost:5173,http://localhost:5174"
  GW_ALLOW="http://localhost:5173"
  ;;
esac

echo "Deploying API stack: $API_STACK (video bucket: $VIDEO_BUCKET)"
COGNITO_OVERRIDE=()
if [[ -n "${COGNITO_USER_POOL_ARN:-}" ]]; then
  COGNITO_OVERRIDE=("CognitoUserPoolArn=${COGNITO_USER_POOL_ARN}")
fi

# Optional: wire the Lambda into the VPC and expose RDS env vars by passing the
# RDS stack name. If unset, the api-stack deploys in DynamoDB-only mode (no VPC
# attachment), which is the default during rollout.
RDS_STACK_OVERRIDE=()
if [[ -n "${RDS_STACK_NAME:-}" ]]; then
  RDS_STACK_OVERRIDE=("RdsStackName=${RDS_STACK_NAME}")
fi

# Feature flag for the DynamoDB -> PostgreSQL cutover. Defaults to 'false' in
# the template; set USE_RDS=true in the env to flip over once the RDS stack is
# deployed and data migrated.
USE_RDS_OVERRIDE=()
if [[ -n "${USE_RDS:-}" ]]; then
  USE_RDS_OVERRIDE=("UseRds=${USE_RDS}")
fi

aws cloudformation deploy \
  --template-file "$TEMPLATE_DIR/api-stack.yaml" \
  --stack-name "$API_STACK" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
  "Environment=${ENV}" \
  "LambdaCodeS3Bucket=${ARTIFACT_BUCKET}" \
  "LambdaCodeS3Key=${ZIP_KEY}" \
  "VideoBucketName=${VIDEO_BUCKET}" \
  "VideoUrl=${BUCKET_URL}" \
  "CorsAllowOrigin=${CORS}" \
  "GatewayResponseAllowOrigin=${GW_ALLOW}" \
  "${COGNITO_OVERRIDE[@]}" \
  "${RDS_STACK_OVERRIDE[@]}" \
  "${USE_RDS_OVERRIDE[@]}"

API_ENDPOINT="$(aws cloudformation describe-stacks \
  --stack-name "$API_STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)"
echo "ApiEndpoint: $API_ENDPOINT"
