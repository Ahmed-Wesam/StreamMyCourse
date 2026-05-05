#!/usr/bin/env bash
# One-time (per env): create Secrets Manager secret via CFN, write private key PEM, publish public key to SSM.
# Usage: deploy-cloudfront-keys-stack.sh <dev|integ|prod> /path/to/private_key.pem /path/to/public_key.pem
set -euo pipefail

ENV="${1:?Usage: $0 <dev|integ|prod> <private.pem> <public.pem>}"
PRIV_PEM="${2:?private pem path}"
PUB_PEM="${3:?public pem path}"

case "$ENV" in
dev | integ | prod) ;;
*)
  echo "Environment must be dev, integ, or prod" >&2
  exit 1
  ;;
esac

REGION="${AWS_REGION:-eu-west-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK="StreamMyCourse-CloudFrontKeys-${ENV}"
SSM_NAME="/streammycourse/${ENV}/cloudfront/signing-public-pem"

[[ -f "$PRIV_PEM" ]] || {
  echo "Missing private key file: $PRIV_PEM" >&2
  exit 1
}
[[ -f "$PUB_PEM" ]] || {
  echo "Missing public key file: $PUB_PEM" >&2
  exit 1
}

echo "Deploying $STACK"
aws cloudformation deploy \
  --template-file "$ROOT/infrastructure/templates/cloudfront-keys-stack.yaml" \
  --stack-name "$STACK" \
  --parameter-overrides "Environment=${ENV}" \
  --capabilities CAPABILITY_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

SECRET_ARN="$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`PrivateKeySecretArn`].OutputValue' \
  --output text)"

echo "Writing private key to $SECRET_ARN"
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ARN" \
  --secret-string "file://${PRIV_PEM}" \
  --region "$REGION"

echo "Publishing public PEM to SSM: $SSM_NAME"
aws ssm put-parameter \
  --name "$SSM_NAME" \
  --type String \
  --value "file://${PUB_PEM}" \
  --overwrite \
  --region "$REGION"

echo "Done. Use these with deploy-backend / video stack:"
echo "  CLOUDFRONT_PUBLIC_KEY_SSM_PARAMETER_NAME=$SSM_NAME"
echo "  CLOUDFRONT_PRIVATE_KEY_SECRET_ARN=$SECRET_ARN"
