#!/usr/bin/env bash
# Deploy StreamMyCourse-ApiWaf-{env}: REGIONAL WAF on the catalog API Gateway stage.
# Requires the api-stack to exist (CatalogApi logical id).
set -euo pipefail

ENV="${1:?Usage: deploy-api-waf.sh <dev|prod>}"
REGION="${AWS_REGION:-eu-west-1}"

case "$ENV" in
dev)
  API_STACK="streammycourse-api"
  ;;
prod)
  API_STACK="StreamMyCourse-Api-prod"
  ;;
*)
  echo "Environment must be dev or prod, got: $ENV" >&2
  exit 1
  ;;
esac

WAF_STACK="StreamMyCourse-ApiWaf-${ENV}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${ROOT}/infrastructure/templates/api-waf-stack.yaml"

REST_API_ID="$(aws cloudformation describe-stack-resources \
  --stack-name "$API_STACK" \
  --region "$REGION" \
  --logical-resource-id CatalogApi \
  --query 'StackResources[0].PhysicalResourceId' \
  --output text)"

if [[ -z "$REST_API_ID" || "$REST_API_ID" == "None" ]]; then
  echo "Failed to resolve CatalogApi from stack $API_STACK" >&2
  exit 1
fi

echo "Deploying API WAF stack $WAF_STACK (RestApiId=$REST_API_ID, region=$REGION)"

aws cloudformation validate-template \
  --template-body "file://${TEMPLATE}" \
  --region "$REGION"

aws cloudformation deploy \
  --template-file "$TEMPLATE" \
  --stack-name "$WAF_STACK" \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "Environment=${ENV}" \
    "CatalogApiRestApiId=${REST_API_ID}" \
    "EnableWafApi=true" \
    "EnableManagedRulesBlock=false" \
    "ApiRateLimit=2000"

echo "API WAF stack $WAF_STACK deployed (or no-op changeset)."
