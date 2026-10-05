#!/usr/bin/env bash
# Ensure streammycourse/hyperpay/prod exists for billing edge (HyperPay credentials).
# Set HYPERPAY_ACCESS_TOKEN, HYPERPAY_ENTITY_ID, and optionally HYPERPAY_WEBHOOK_SECRET
# (GitHub Actions secrets or env) when creating or rotating credentials.
set -euo pipefail

SECRET_ID="${HYPERPAY_SECRET_ID:-streammycourse/hyperpay/prod}"
REGION="${AWS_REGION:-eu-west-1}"

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

build_secret_json() {
  local token="$1"
  local entity="$2"
  local webhook="${3:-}"
  jq -n \
    --arg token "$token" \
    --arg entity "$entity" \
    --arg webhook "$webhook" \
    '{
      access_token: $token,
      entity_id: $entity,
      api_host: "eu-test.oppwa.com"
    }
    + (if ($webhook | length) > 0 then {webhook_secret: $webhook} else {} end)'
}

if aws secretsmanager describe-secret --secret-id "$SECRET_ID" --region "$REGION" >/dev/null 2>&1; then
  current="$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_ID" \
    --region "$REGION" \
    --query SecretString \
    --output text)"
  existing_token="$(echo "$current" | jq -r '.access_token // empty' 2>/dev/null || true)"
  existing_entity="$(echo "$current" | jq -r '.entity_id // empty' 2>/dev/null || true)"
  if [[ -n "${HYPERPAY_ACCESS_TOKEN:-}" || -n "${HYPERPAY_ENTITY_ID:-}" || -n "${HYPERPAY_WEBHOOK_SECRET:-}" ]]; then
    merged="$(echo "$current" | jq \
      --arg token "${HYPERPAY_ACCESS_TOKEN:-}" \
      --arg entity "${HYPERPAY_ENTITY_ID:-}" \
      --arg webhook "${HYPERPAY_WEBHOOK_SECRET:-}" \
      '
        if ($token | length) > 0 then .access_token = $token else . end
        | if ($entity | length) > 0 then .entity_id = $entity else . end
        | if ($webhook | length) > 0 then .webhook_secret = $webhook else . end
      ')"
    aws secretsmanager put-secret-value \
      --secret-id "$SECRET_ID" \
      --region "$REGION" \
      --secret-string "$merged" >/dev/null
    echo "Updated HyperPay credentials in existing secret: $SECRET_ID"
  elif [[ -z "$existing_token" || -z "$existing_entity" ]]; then
    echo "HyperPay secret $SECRET_ID exists but access_token or entity_id is empty. Set HYPERPAY_ACCESS_TOKEN and HYPERPAY_ENTITY_ID (GitHub prod secrets or env) and re-run." >&2
    exit 1
  else
    echo "HyperPay secret already exists: $SECRET_ID"
  fi
else
  if [[ -z "${HYPERPAY_ACCESS_TOKEN:-}" || -z "${HYPERPAY_ENTITY_ID:-}" ]]; then
    echo "Missing HyperPay credentials. Set GitHub secrets HYPERPAY_ACCESS_TOKEN and HYPERPAY_ENTITY_ID or export them before deploy." >&2
    exit 1
  fi
  aws secretsmanager create-secret \
    --name "$SECRET_ID" \
    --region "$REGION" \
    --description "HyperPay credentials for billing edge (prod)" \
    --secret-string "$(build_secret_json "$HYPERPAY_ACCESS_TOKEN" "$HYPERPAY_ENTITY_ID" "${HYPERPAY_WEBHOOK_SECRET:-}")" >/dev/null
  echo "Created HyperPay secret: $SECRET_ID"
fi

ARN="$(aws secretsmanager describe-secret \
  --secret-id "$SECRET_ID" \
  --region "$REGION" \
  --query ARN \
  --output text)"
if [[ -z "$ARN" || "$ARN" == "None" ]]; then
  echo "Failed to resolve ARN for $SECRET_ID" >&2
  exit 1
fi
echo "HYPERPAY_SECRET_ARN=$ARN"
