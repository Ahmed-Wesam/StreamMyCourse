#!/usr/bin/env bash
# Deploy video (S3) + API (Lambda, API Gateway, RDS-backed catalog) for one environment.
# Mirrors infrastructure/deploy-environment.ps1 for use in CI (Linux) or locally (Git Bash / WSL).
set -euo pipefail

ENV="${1:?Usage: deploy-backend.sh <dev|prod>}"
case "$ENV" in
dev | prod) ;;
*)
  echo "Environment must be dev or prod, got: $ENV" >&2
  exit 1
  ;;
esac

REGION="${AWS_REGION:-eu-west-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT/infrastructure/templates"
LAMBDA_DIR="$ROOT/infrastructure/lambda/catalog"
AUTH_LAMBDA_DIR="$ROOT/infrastructure/lambda/catalog_token_authorizer"

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
AUTH_ZIP_KEY="catalog-token-authorizer-${ENV}-${SUFFIX}.zip"

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
AUTH_ZIP="/tmp/catalog-token-authorizer-${ENV}-$$.zip"
AUTH_BUILD_DIR="/tmp/catalog-token-authorizer-build-${ENV}-$$"
trap 'rm -f "$ZIP" "$AUTH_ZIP"; rm -rf "$BUILD_DIR" "$AUTH_BUILD_DIR"' EXIT
[[ -d "$LAMBDA_DIR" ]] || {
  echo "Lambda source directory missing: $LAMBDA_DIR" >&2
  exit 1
}
[[ -d "$AUTH_LAMBDA_DIR" ]] || {
  echo "Token authorizer source directory missing: $AUTH_LAMBDA_DIR" >&2
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

_zip_dir_recursive() {
  local src="$1"
  local out="$2"
  if command -v zip >/dev/null 2>&1; then
    ( cd "$src" && zip -rq "$out" . )
    return
  fi
  local py=""
  if command -v python3 >/dev/null 2>&1; then
    py="python3"
  elif command -v python >/dev/null 2>&1; then
    py="python"
  else
    echo "Neither zip(1) nor python3/python found; install Info-ZIP zip or Python to build Lambda bundles." >&2
    exit 1
  fi
  "$py" - "$src" "$out" <<'PY'
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(src):
        for name in files:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                zf.write(path, os.path.relpath(path, src))
PY
}

_zip_one_file() {
  local dir="$1"
  local file="$2"
  local out="$3"
  if command -v zip >/dev/null 2>&1; then
    ( cd "$dir" && zip -jq "$out" "$file" )
    return
  fi
  local py=""
  if command -v python3 >/dev/null 2>&1; then
    py="python3"
  elif command -v python >/dev/null 2>&1; then
    py="python"
  else
    echo "Neither zip(1) nor python3/python found; install Info-ZIP zip or Python." >&2
    exit 1
  fi
  "$py" - "$dir" "$file" "$out" <<'PY'
import os, sys, zipfile
d, fn, out = sys.argv[1], sys.argv[2], sys.argv[3]
path = os.path.join(d, fn)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(path, fn)
PY
}

_zip_dir_recursive "$BUILD_DIR" "$ZIP"
echo "Uploading Lambda s3://${ARTIFACT_BUCKET}/${ZIP_KEY}"
aws s3 cp "$ZIP" "s3://${ARTIFACT_BUCKET}/${ZIP_KEY}" --region "$REGION"

# --- TOKEN authorizer Lambda bundle (outside VPC) -------------------------------

rm -rf "$AUTH_BUILD_DIR"
mkdir -p "$AUTH_BUILD_DIR"
( cd "$AUTH_LAMBDA_DIR" && \
  find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
    | xargs -0 -I{} cp --parents '{}' "$AUTH_BUILD_DIR" )

AUTH_REQ_FILE="$AUTH_LAMBDA_DIR/requirements.txt"
if [[ -f "$AUTH_REQ_FILE" ]]; then
  echo "Installing TOKEN authorizer runtime deps into $AUTH_BUILD_DIR/_vendor"
  pip install \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    -r "$AUTH_REQ_FILE" \
    -t "$AUTH_BUILD_DIR/_vendor"
fi

_zip_dir_recursive "$AUTH_BUILD_DIR" "$AUTH_ZIP"
echo "Uploading TOKEN authorizer s3://${ARTIFACT_BUCKET}/${AUTH_ZIP_KEY}"
aws s3 cp "$AUTH_ZIP" "s3://${ARTIFACT_BUCKET}/${AUTH_ZIP_KEY}" --region "$REGION"

INV_ZIP="/tmp/cf-invalidate-${ENV}-$$.zip"
INV_KEY="cf-invalidate-${ENV}-${SUFFIX}.zip"
CF_INV_DIR="${ROOT}/infrastructure/lambda/cloudfront_invalidation"
if [[ ! -f "${CF_INV_DIR}/index.py" ]]; then
  echo "Missing CloudFront invalidation Lambda: ${CF_INV_DIR}/index.py" >&2
  exit 1
fi
_zip_one_file "$CF_INV_DIR" "index.py" "$INV_ZIP"
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

# Async S3 cleanup (SQS + worker) for dev and prod. Override both URL and ARN to reuse
# pre-deployed queue without running the media-cleanup stack again.
MEDIA_QUEUE_URL="${MEDIA_CLEANUP_QUEUE_URL:-}"
MEDIA_QUEUE_ARN="${MEDIA_CLEANUP_QUEUE_ARN:-}"
case "$ENV" in
dev | prod)
  if [[ -z "$MEDIA_QUEUE_URL" || -z "$MEDIA_QUEUE_ARN" ]]; then
    MC_SCRIPT="${ROOT}/scripts/deploy-media-cleanup.sh"
    chmod +x "$MC_SCRIPT"
    "$MC_SCRIPT" "$ENV" "$REGION" "$ARTIFACT_BUCKET" "$SUFFIX"
    MEDIA_STACK="StreamMyCourse-MediaCleanup-${ENV}"
    MEDIA_QUEUE_URL="$(aws cloudformation describe-stacks \
      --stack-name "$MEDIA_STACK" \
      --region "$REGION" \
      --query 'Stacks[0].Outputs[?OutputKey==`MediaCleanupQueueUrl`].OutputValue' \
      --output text)"
    MEDIA_QUEUE_ARN="$(aws cloudformation describe-stacks \
      --stack-name "$MEDIA_STACK" \
      --region "$REGION" \
      --query 'Stacks[0].Outputs[?OutputKey==`MediaCleanupQueueArn`].OutputValue' \
      --output text)"
    if [[ -z "$MEDIA_QUEUE_URL" || "$MEDIA_QUEUE_URL" == "None" || -z "$MEDIA_QUEUE_ARN" || "$MEDIA_QUEUE_ARN" == "None" ]]; then
      echo "Failed to read media cleanup stack outputs (queue URL / ARN)" >&2
      exit 1
    fi
  fi
  ;;
esac

MEDIA_PARAM_OVERRIDES=()
if [[ -n "${MEDIA_QUEUE_URL:-}" && -n "${MEDIA_QUEUE_ARN:-}" ]]; then
  MEDIA_PARAM_OVERRIDES=("MediaCleanupQueueUrl=${MEDIA_QUEUE_URL}" "MediaCleanupQueueArn=${MEDIA_QUEUE_ARN}")
fi

case "$ENV" in
prod)
  API_STACK="StreamMyCourse-Api-prod"
  CORS="https://app.streammycourse.click,https://teach.streammycourse.click,http://localhost:5173,http://localhost:5174"
  GW_ALLOW="https://app.streammycourse.click"
  ;;
dev)
  API_STACK="streammycourse-api"
  CORS="https://dev.streammycourse.click,https://teach.dev.streammycourse.click,http://localhost:5173,http://localhost:5174"
  GW_ALLOW="http://localhost:5173"
  ;;
esac

echo "Deploying API stack: $API_STACK (video bucket: $VIDEO_BUCKET)"
# JWT audience validation in the TOKEN authorizer must accept every app client that mints
# IdTokens for this API (teacher + student). CI integration tests mint both audiences.
AUTH_STACK_NAME="StreamMyCourse-Auth-${ENV}"
COGNITO_CLIENT_IDS="${COGNITO_CLIENT_IDS:-}"
if [[ -z "${COGNITO_CLIENT_IDS}" ]]; then
  if aws cloudformation describe-stacks --stack-name "$AUTH_STACK_NAME" --region "$REGION" &>/dev/null; then
    TEACHER_CLIENT="$(aws cloudformation describe-stacks \
      --stack-name "$AUTH_STACK_NAME" \
      --region "$REGION" \
      --query "Stacks[0].Outputs[?OutputKey=='TeacherUserPoolClientId'].OutputValue" \
      --output text)"
    STUDENT_CLIENT="$(aws cloudformation describe-stacks \
      --stack-name "$AUTH_STACK_NAME" \
      --region "$REGION" \
      --query "Stacks[0].Outputs[?OutputKey=='StudentUserPoolClientId'].OutputValue" \
      --output text)"
    CID_PARTS=()
    if [[ -n "${TEACHER_CLIENT}" && "${TEACHER_CLIENT}" != "None" ]]; then
      CID_PARTS+=("${TEACHER_CLIENT}")
    fi
    if [[ -n "${STUDENT_CLIENT}" && "${STUDENT_CLIENT}" != "None" && "${STUDENT_CLIENT}" != "${TEACHER_CLIENT}" ]]; then
      CID_PARTS+=("${STUDENT_CLIENT}")
    fi
    if ((${#CID_PARTS[@]})); then
      COGNITO_CLIENT_IDS="$(IFS=,; echo "${CID_PARTS[*]}")"
    fi
  fi
fi
if [[ -z "${COGNITO_CLIENT_IDS}" ]]; then
  if aws cloudformation describe-stacks --stack-name "$AUTH_STACK_NAME" --region "$REGION" &>/dev/null; then
    echo >&2 "Warning: could not derive non-empty Cognito client ids from ${AUTH_STACK_NAME}; CognitoClientId parameter not overridden (existing API stack value kept when updating)."
  else
    echo >&2 "Note: auth stack ${AUTH_STACK_NAME} not found; Cognito client ids not auto-filled. Existing API stack value kept when updating. Set COGNITO_CLIENT_IDS to override explicitly."
  fi
fi

COGNITO_OVERRIDE=()
if [[ -n "${COGNITO_USER_POOL_ARN:-}" ]]; then
  COGNITO_OVERRIDE+=("CognitoUserPoolArn=${COGNITO_USER_POOL_ARN}")
fi
if [[ -n "${COGNITO_CLIENT_IDS}" ]]; then
  COGNITO_OVERRIDE+=("CognitoClientId=${COGNITO_CLIENT_IDS}")
fi

# Catalog Lambda requires VPC + DB_* from the RDS stack exports.
RDS_STACK_NAME="${RDS_STACK_NAME:-StreamMyCourse-Rds-${ENV}}"
RDS_STACK_OVERRIDE=("RdsStackName=${RDS_STACK_NAME}")

# Validate RDS stack exists before deploying API stack
if ! aws cloudformation describe-stacks --stack-name "$RDS_STACK_NAME" --region "$REGION" &>/dev/null; then
    echo "Error: RDS stack '$RDS_STACK_NAME' not found. Deploy the RDS stack first." >&2
    exit 1
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
  "TokenAuthorizerCodeS3Key=${AUTH_ZIP_KEY}" \
  "VideoBucketName=${VIDEO_BUCKET}" \
  "VideoUrl=${BUCKET_URL}" \
  "CorsAllowOrigin=${CORS}" \
  "GatewayResponseAllowOrigin=${GW_ALLOW}" \
  "${COGNITO_OVERRIDE[@]}" \
  "${RDS_STACK_OVERRIDE[@]}" \
  "${MEDIA_PARAM_OVERRIDES[@]}"

API_ENDPOINT="$(aws cloudformation describe-stacks \
  --stack-name "$API_STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)"
echo "ApiEndpoint: $API_ENDPOINT"
