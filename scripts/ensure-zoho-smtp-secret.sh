#!/usr/bin/env bash
# Ensure streammycourse/zoho-smtp/prod exists for Cognito CustomEmailSender (Zoho SMTP).
# Set ZOHO_SMTP_PASSWORD (GitHub Actions secret or env) when creating or rotating the app password.
set -euo pipefail

SECRET_ID="${ZOHO_SMTP_SECRET_ID:-streammycourse/zoho-smtp/prod}"
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
  local pw="$1"
  jq -n \
    --arg pw "$pw" \
    '{
      smtp_host: "smtp.zoho.com",
      smtp_port: 587,
      smtp_username: "support@researchspectrum.org",
      smtp_password: $pw,
      from_address: "Research Spectrum <noreply@researchspectrum.org>",
      reply_to: "support@researchspectrum.org"
    }'
}

if aws secretsmanager describe-secret --secret-id "$SECRET_ID" --region "$REGION" >/dev/null 2>&1; then
  current="$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_ID" \
    --region "$REGION" \
    --query SecretString \
    --output text)"
  existing_pw="$(echo "$current" | jq -r '.smtp_password // empty' 2>/dev/null || true)"
  if [[ -n "${ZOHO_SMTP_PASSWORD:-}" ]]; then
    merged="$(echo "$current" | jq --arg pw "$ZOHO_SMTP_PASSWORD" '.smtp_password = $pw')"
    aws secretsmanager put-secret-value \
      --secret-id "$SECRET_ID" \
      --region "$REGION" \
      --secret-string "$merged" >/dev/null
    echo "Updated Zoho SMTP password in existing secret: $SECRET_ID"
  elif [[ -z "$existing_pw" ]]; then
    echo "Zoho SMTP secret $SECRET_ID exists but smtp_password is empty. Set ZOHO_SMTP_PASSWORD (GitHub prod secret or env) and re-run." >&2
    exit 1
  else
    echo "Zoho SMTP secret already exists: $SECRET_ID"
  fi
else
  if [[ -z "${ZOHO_SMTP_PASSWORD:-}" ]]; then
    echo "Missing Zoho SMTP app password. Set GitHub secret ZOHO_SMTP_PASSWORD or export ZOHO_SMTP_PASSWORD before deploy." >&2
    exit 1
  fi
  aws secretsmanager create-secret \
    --name "$SECRET_ID" \
    --region "$REGION" \
    --description "Zoho SMTP credentials for Cognito CustomEmailSender (prod)" \
    --secret-string "$(build_secret_json "$ZOHO_SMTP_PASSWORD")" >/dev/null
  echo "Created Zoho SMTP secret: $SECRET_ID"
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
echo "ZOHO_SMTP_SECRET_ARN=$ARN"
