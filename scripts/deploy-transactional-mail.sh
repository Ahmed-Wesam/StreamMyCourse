#!/usr/bin/env bash
# Deploy StreamMyCourse-TransactionalMail-prod: SQS + DLQ + Lambda worker (Zoho SMTP).
# Deploy for prod (same naming as deploy-backend.sh).
set -euo pipefail

ENV="${1:?Usage: deploy-transactional-mail.sh <prod> <region> <artifact_bucket> <suffix>}"
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
LAMBDA_DIR="$ROOT/infrastructure/lambda/transactional_mail"

MAIL_STACK="StreamMyCourse-TransactionalMail-${ENV}"

ZOHO_ARN="${ZOHO_SMTP_SECRET_ARN:-}"
if [[ -z "$ZOHO_ARN" ]]; then
  SECRET_ID="${ZOHO_SMTP_SECRET_ID:-streammycourse/zoho-smtp/prod}"
  ZOHO_ARN="$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_ID" \
    --region "$REGION" \
    --query ARN \
    --output text 2>/dev/null || true)"
fi
if [[ -z "$ZOHO_ARN" || "$ZOHO_ARN" == "None" ]]; then
  echo "Zoho SMTP secret ARN required. Set ZOHO_SMTP_SECRET_ARN or create ${ZOHO_SMTP_SECRET_ID:-streammycourse/zoho-smtp/prod}." >&2
  exit 1
fi

[[ -f "${LAMBDA_DIR}/worker.py" ]] || {
  echo "Missing transactional mail Lambda: ${LAMBDA_DIR}/worker.py" >&2
  exit 1
}

ZIP="/tmp/transactional-mail-${ENV}-$$.zip"
TM_BUILD="/tmp/transactional-mail-build-${ENV}-$$"
ZIP_KEY="transactional-mail-${ENV}-${SUFFIX}.zip"
trap 'rm -f "$ZIP"; rm -rf "$TM_BUILD"' EXIT

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

rm -rf "$TM_BUILD"
mkdir -p "$TM_BUILD"
( cd "$LAMBDA_DIR" && \
  find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
    | xargs -0 -I{} cp --parents '{}' "$TM_BUILD" )

_zip_dir_recursive "$TM_BUILD" "$ZIP"

echo "Uploading transactional mail Lambda s3://${ARTIFACT_BUCKET}/${ZIP_KEY}"
aws s3 cp "$ZIP" "s3://${ARTIFACT_BUCKET}/${ZIP_KEY}" --region "$REGION"

MAIL_TEMPLATE="${TEMPLATE_DIR}/transactional-mail-stack.yaml"
if command -v cygpath >/dev/null 2>&1; then
  VALIDATE_BODY_URI="file://$(cygpath -m "$MAIL_TEMPLATE")"
else
  VALIDATE_BODY_URI="file://${MAIL_TEMPLATE}"
fi
aws cloudformation validate-template \
  --template-body "$VALIDATE_BODY_URI" \
  --region "$REGION"

echo "Deploying transactional mail stack: $MAIL_STACK"
CATALOG_ROLE_OVERRIDES=()
if [[ -n "${CATALOG_LAMBDA_ROLE_ARN:-}" ]]; then
  CATALOG_ROLE_OVERRIDES=("CatalogLambdaRoleArn=${CATALOG_LAMBDA_ROLE_ARN}")
fi
aws cloudformation deploy \
  --template-file "$TEMPLATE_DIR/transactional-mail-stack.yaml" \
  --stack-name "$MAIL_STACK" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
  "Environment=${ENV}" \
  "LambdaCodeS3Bucket=${ARTIFACT_BUCKET}" \
  "LambdaCodeS3Key=${ZIP_KEY}" \
  "ZohoSmtpSecretArn=${ZOHO_ARN}" \
  "${CATALOG_ROLE_OVERRIDES[@]}"
