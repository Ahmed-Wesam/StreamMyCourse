#!/usr/bin/env bash
# Deploy StreamMyCourse-VideoProviderEdge-{env}: no-VPC Kinescope upload/webhook edge.
set -euo pipefail

ENV="${1:?Usage: deploy-video-provider-edge.sh <prod> <region> <artifact_bucket> <suffix>}"
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
EDGE_DIR="$ROOT/infrastructure/lambda/video_provider_edge"

VIDEO_EDGE_STACK="StreamMyCourse-VideoProviderEdge-${ENV}"

CATALOG_LAMBDA_ARN="${CATALOG_LAMBDA_ARN:-}"
KINESCOPE_API_TOKEN="${KINESCOPE_API_TOKEN:-}"
KINESCOPE_PARENT_ID="${KINESCOPE_PARENT_ID:-}"
KINESCOPE_WEBHOOK_SECRET="${KINESCOPE_WEBHOOK_SECRET:-}"
CORS_ALLOW_ORIGIN="${CORS_ALLOW_ORIGIN:-}"

if [[ -z "$KINESCOPE_API_TOKEN" || -z "$KINESCOPE_PARENT_ID" ]]; then
  echo "Error: deploy-video-provider-edge requires KINESCOPE_API_TOKEN and KINESCOPE_PARENT_ID." >&2
  exit 1
fi

[[ -d "$EDGE_DIR" ]] || {
  echo "Missing video provider edge Lambda: $EDGE_DIR" >&2
  exit 1
}
[[ -f "${EDGE_DIR}/handler.py" ]] || {
  echo "Missing video provider edge handler: ${EDGE_DIR}/handler.py" >&2
  exit 1
}

EDGE_ZIP="/tmp/video-provider-edge-${ENV}-$$.zip"
EDGE_BUILD="/tmp/video-provider-edge-build-${ENV}-$$"
ZIP_KEY="video-provider-edge-${ENV}-${SUFFIX}.zip"
trap 'rm -f "$EDGE_ZIP"; rm -rf "$EDGE_BUILD"' EXIT

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

rm -rf "$EDGE_BUILD"
mkdir -p "$EDGE_BUILD"
( cd "$EDGE_DIR" && \
  find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
    | xargs -0 -I{} cp --parents '{}' "$EDGE_BUILD" )

REQ_FILE="$EDGE_DIR/requirements.txt"
if [[ -f "$REQ_FILE" ]] && grep -qvE '^\s*($|#)' "$REQ_FILE" 2>/dev/null; then
  echo "Installing video provider edge runtime deps into $EDGE_BUILD/_vendor"
  pip install \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    -r "$REQ_FILE" \
    -t "$EDGE_BUILD/_vendor"
fi

_zip_dir_recursive "$EDGE_BUILD" "$EDGE_ZIP"

echo "Uploading video provider edge s3://${ARTIFACT_BUCKET}/${ZIP_KEY}"
aws s3 cp "$EDGE_ZIP" "s3://${ARTIFACT_BUCKET}/${ZIP_KEY}" --region "$REGION"

EDGE_TEMPLATE="${TEMPLATE_DIR}/video-provider-edge-stack.yaml"
if command -v cygpath >/dev/null 2>&1; then
  VALIDATE_BODY_URI="file://$(cygpath -m "$EDGE_TEMPLATE")"
else
  VALIDATE_BODY_URI="file://${EDGE_TEMPLATE}"
fi
aws cloudformation validate-template \
  --template-body "$VALIDATE_BODY_URI" \
  --region "$REGION"

echo "Deploying video provider edge stack: $VIDEO_EDGE_STACK"
EDGE_PARAM_OVERRIDES=(
  "Environment=${ENV}"
  "LambdaCodeS3Bucket=${ARTIFACT_BUCKET}"
  "LambdaCodeS3Key=${ZIP_KEY}"
  "CatalogLambdaArn=${CATALOG_LAMBDA_ARN}"
  "KinescopeApiToken=${KINESCOPE_API_TOKEN}"
  "KinescopeParentId=${KINESCOPE_PARENT_ID}"
  "KinescopeWebhookSecret=${KINESCOPE_WEBHOOK_SECRET}"
)
if [[ -n "$CORS_ALLOW_ORIGIN" ]]; then
  EDGE_PARAM_OVERRIDES+=("CorsAllowOrigin=${CORS_ALLOW_ORIGIN}")
fi

aws cloudformation deploy \
  --template-file "$EDGE_TEMPLATE" \
  --stack-name "$VIDEO_EDGE_STACK" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
  "${EDGE_PARAM_OVERRIDES[@]}"
