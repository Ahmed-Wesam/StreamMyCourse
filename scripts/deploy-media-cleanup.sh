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

( cd "$LAMBDA_DIR" && zip -jq "$ZIP" worker.py )

echo "Uploading media cleanup Lambda s3://${ARTIFACT_BUCKET}/${ZIP_KEY}"
aws s3 cp "$ZIP" "s3://${ARTIFACT_BUCKET}/${ZIP_KEY}" --region "$REGION"

aws cloudformation validate-template \
  --template-body "file://${TEMPLATE_DIR}/media-cleanup-stack.yaml" \
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
