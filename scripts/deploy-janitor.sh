#!/usr/bin/env bash
# Deploy the Artifact Janitor Lambda for scheduled S3 cleanup.
# Usage: deploy-janitor.sh [dev|integ|prod] [keep-count] [dry-run]
set -euo pipefail

ENV="${1:-dev}"
KEEP_COUNT="${2:-2}"
DRY_RUN="${3:-false}"

REGION="${AWS_REGION:-eu-west-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT/infrastructure/templates"
LAMBDA_DIR="$ROOT/infrastructure/lambda/artifact_janitor"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
ARTIFACT_BUCKET="streammycourse-artifacts-${ACCOUNT}-${REGION}"
STACK_NAME="StreamMyCourse-ArtifactJanitor-${ENV}"

echo "=== Deploying Artifact Janitor ==="
echo "Environment: $ENV"
echo "Artifact bucket: $ARTIFACT_BUCKET"
echo "Keep count: $KEEP_COUNT"
echo "Dry run: $DRY_RUN"
echo ""

# Package Lambda code
ZIP="/tmp/artifact-janitor-${ENV}-$$.zip"
trap 'rm -f "$ZIP"' EXIT

echo "Packaging Lambda code..."
(cd "$LAMBDA_DIR" && zip -rq "$ZIP" .)

# Check if stack exists - if not, create with placeholder code first
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &>/dev/null; then
    echo "Stack does not exist. Creating initial stack..."
    aws cloudformation deploy \
        --template-file "$TEMPLATE_DIR/artifact-janitor-stack.yaml" \
        --stack-name "$STACK_NAME" \
        --capabilities CAPABILITY_IAM \
        --region "$REGION" \
        --no-fail-on-empty-changeset \
        --parameter-overrides \
            "Environment=${ENV}" \
            "ArtifactBucketName=${ARTIFACT_BUCKET}" \
            "KeepCount=${KEEP_COUNT}" \
            "DryRun=${DRY_RUN}"
fi

# Update Lambda code
echo "Updating Lambda function code..."
FUNCTION_NAME="StreamMyCourse-ArtifactJanitor-${ENV}"
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://${ZIP}" \
    --region "$REGION" \
    --publish

echo ""
echo "Updating stack parameters..."
aws cloudformation deploy \
    --template-file "$TEMPLATE_DIR/artifact-janitor-stack.yaml" \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
        "Environment=${ENV}" \
        "ArtifactBucketName=${ARTIFACT_BUCKET}" \
        "KeepCount=${KEEP_COUNT}" \
        "DryRun=${DRY_RUN}"

echo ""
echo "=== Deployment Complete ==="
echo "Stack: $STACK_NAME"
echo "Function: $FUNCTION_NAME"
echo "Schedule: Daily (rate: 1 day)"
echo ""
echo "To trigger manually:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --region $REGION /dev/null"
echo ""
echo "To view logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --follow"
