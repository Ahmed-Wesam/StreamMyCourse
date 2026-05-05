#!/usr/bin/env bash
# Deploy StreamMyCourse-MediaCleanup-{env}: SQS + DLQ + Lambda worker for async S3 deletes.
# Deploy for dev or prod (same video stack naming as deploy-backend.sh).
set -euo pipefail

ENV="${1:?Usage: deploy-media-cleanup.sh <dev|prod> <region> <artifact_bucket> <suffix>}"
REGION="${2:?region}"
ARTIFACT_BUCKET="${3:?artifact bucket}"
SUFFIX="${4:?suffix}"

case "$ENV" in
dev | prod) ;;
*)
  echo "Environment must be dev or prod, got: $ENV" >&2
  exit 1
  ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT/infrastructure/templates"
LAMBDA_DIR="$ROOT/infrastructure/lambda/media_cleanup"

VIDEO_STACK="StreamMyCourse-Video-${ENV}"
MEDIA_STACK="StreamMyCourse-MediaCleanup-${ENV}"

VIDEO_BUCKET="$(aws cloudformation describe-stacks \
  --stack-name "$VIDEO_STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)"

if [[ -z "$VIDEO_BUCKET" || "$VIDEO_BUCKET" == "None" ]]; then
  echo "Failed to read BucketName from $VIDEO_STACK" >&2
  exit 1
fi

if [[ ! -f "${LAMBDA_DIR}/worker.py" ]]; then
  echo "Missing media cleanup Lambda: ${LAMBDA_DIR}/worker.py" >&2
  exit 1
fi

ZIP="/tmp/media-cleanup-${ENV}-$$.zip"
ZIP_KEY="media-cleanup-${ENV}-${SUFFIX}.zip"
trap 'rm -f "$ZIP"' EXIT

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

_zip_one_file "$LAMBDA_DIR" "worker.py" "$ZIP"

echo "Uploading media cleanup Lambda s3://${ARTIFACT_BUCKET}/${ZIP_KEY}"
aws s3 cp "$ZIP" "s3://${ARTIFACT_BUCKET}/${ZIP_KEY}" --region "$REGION"

# Git Bash: AWS CLI often rejects file:///c/... URIs for --template-body; use a Windows path when cygpath exists.
MEDIA_TEMPLATE="${TEMPLATE_DIR}/media-cleanup-stack.yaml"
if command -v cygpath >/dev/null 2>&1; then
  VALIDATE_BODY_URI="file://$(cygpath -m "$MEDIA_TEMPLATE")"
else
  VALIDATE_BODY_URI="file://${MEDIA_TEMPLATE}"
fi
aws cloudformation validate-template \
  --template-body "$VALIDATE_BODY_URI" \
  --region "$REGION"

echo "Deploying media cleanup stack: $MEDIA_STACK"
aws cloudformation deploy \
  --template-file "$TEMPLATE_DIR/media-cleanup-stack.yaml" \
  --stack-name "$MEDIA_STACK" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
  "Environment=${ENV}" \
  "VideoBucketName=${VIDEO_BUCKET}" \
  "LambdaCodeS3Bucket=${ARTIFACT_BUCKET}" \
  "LambdaCodeS3Key=${ZIP_KEY}"
