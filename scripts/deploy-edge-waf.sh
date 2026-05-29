#!/usr/bin/env bash
# Deploy StreamMyCourse-EdgeWaf-{env}: CLOUDFRONT WAF on the student distribution (us-east-1).
# Requires edge-hosting-stack StudentDistributionId output.
set -euo pipefail

ENV="${1:?Usage: deploy-edge-waf.sh <dev|prod>}"
EDGE_REGION="${EDGE_WAF_REGION:-us-east-1}"

case "$ENV" in
dev | prod) ;;
*)
  echo "Environment must be dev or prod, got: $ENV" >&2
  exit 1
  ;;
esac

EDGE_STACK="StreamMyCourse-EdgeHosting-${ENV}"
WAF_STACK="StreamMyCourse-EdgeWaf-${ENV}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${ROOT}/infrastructure/templates/edge-waf-stack.yaml"

DIST_ID="$(aws cloudformation describe-stacks \
  --stack-name "$EDGE_STACK" \
  --region "$EDGE_REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='StudentDistributionId'].OutputValue | [0]" \
  --output text)"

if [[ -z "$DIST_ID" || "$DIST_ID" == "None" ]]; then
  echo "Failed to resolve StudentDistributionId from stack $EDGE_STACK (region=$EDGE_REGION)" >&2
  exit 1
fi

echo "Deploying edge WAF stack $WAF_STACK (distribution=$DIST_ID, region=$EDGE_REGION)"

aws cloudformation validate-template \
  --template-body "file://${TEMPLATE}" \
  --region "$EDGE_REGION"

aws cloudformation deploy \
  --template-file "$TEMPLATE" \
  --stack-name "$WAF_STACK" \
  --region "$EDGE_REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "Environment=${ENV}" \
    "StudentDistributionId=${DIST_ID}" \
    "EnableWafEdge=true" \
    "EdgeStaticRateLimit=5000"

echo "Edge WAF stack $WAF_STACK deployed (or no-op changeset)."
