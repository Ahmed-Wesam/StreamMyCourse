#!/usr/bin/env bash
# Deploy StreamMyCourse-MediaCleanup-prod: SQS + DLQ + Lambda worker for async S3 deletes.
# Deploy for prod (same video stack naming as deploy-backend.sh).
set -euo pipefail

ENV="${1:?Usage: deploy-media-cleanup.sh <prod> <region> <artifact_bucket> <suffix>}"
REGION="${2:?region}"
ARTIFACT_BUCKET="${3:?artifact bucket}"
SUFFIX="${4:?suffix}"

case "$ENV" in
prod) ;;
*)
  echo "Environment must be prod, got: $ENV" >&2
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

[[ -f "${LAMBDA_DIR}/worker.py" ]] || {
  echo "Missing media cleanup Lambda: ${LAMBDA_DIR}/worker.py" >&2
  exit 1
}
[[ -f "${LAMBDA_DIR}/kinescope_adapter.py" ]] || {
  echo "Missing media cleanup Kinescope adapter: ${LAMBDA_DIR}/kinescope_adapter.py" >&2
  exit 1
}

ZIP="/tmp/media-cleanup-${ENV}-$$.zip"
MC_BUILD="/tmp/media-cleanup-build-${ENV}-$$"
ZIP_KEY="media-cleanup-${ENV}-${SUFFIX}.zip"
trap 'rm -f "$ZIP"; rm -rf "$MC_BUILD"' EXIT

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
    echo "Neither zip(1) nor python3/python found; install Info-ZIP zip or Python." >&2
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

rm -rf "$MC_BUILD"
mkdir -p "$MC_BUILD"
( cd "$LAMBDA_DIR" && \
  find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
    | xargs -0 -I{} cp --parents '{}' "$MC_BUILD" )

_zip_dir_recursive "$MC_BUILD" "$ZIP"

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
MC_KINESCOPE_OVERRIDES=()
if [[ -n "${KINESCOPE_API_TOKEN:-}" ]]; then
  MC_KINESCOPE_OVERRIDES=("KinescopeApiToken=${KINESCOPE_API_TOKEN}")
fi
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
  "LambdaCodeS3Key=${ZIP_KEY}" \
  "${MC_KINESCOPE_OVERRIDES[@]}"
