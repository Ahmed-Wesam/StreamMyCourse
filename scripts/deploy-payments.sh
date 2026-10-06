#!/usr/bin/env bash
# Deploy StreamMyCourse-Payments-prod: billing edge + fulfillment SQS/Lambda (WS2).
set -euo pipefail

ENV="${1:?Usage: deploy-payments.sh <prod> <region> <artifact_bucket> <suffix>}"
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
EDGE_DIR="$ROOT/infrastructure/lambda/billing_edge"
FULFILL_DIR="$ROOT/infrastructure/lambda/billing_fulfillment"

PAYMENTS_STACK="StreamMyCourse-Payments-${ENV}"
RDS_STACK="${RDS_STACK_NAME:-StreamMyCourse-Rds-${ENV}}"

CATALOG_LAMBDA_ARN="${CATALOG_LAMBDA_ARN:-}"
BILLING_SHOPPER_RESULT_URL="${BILLING_SHOPPER_RESULT_URL:-}"
CORS="${CORS:-https://researchspectrum.org,https://teach.researchspectrum.org,http://localhost:5173,http://localhost:5174}"

_resolve_billing_shopper_result_url() {
  if [[ -n "${BILLING_SHOPPER_RESULT_URL}" ]]; then
    return 0
  fi
  local edge_stack="StreamMyCourse-EdgeHosting-${ENV}"
  local edge_region="${EDGE_REGION:-us-east-1}"
  local student_url=""
  if aws cloudformation describe-stacks --stack-name "$edge_stack" --region "$edge_region" &>/dev/null; then
    student_url="$(aws cloudformation describe-stacks \
      --stack-name "$edge_stack" \
      --region "$edge_region" \
      --query 'Stacks[0].Outputs[?OutputKey==`StudentSiteUrl`].OutputValue' \
      --output text)"
  fi
  if [[ -n "${student_url}" && "${student_url}" != "None" ]]; then
    BILLING_SHOPPER_RESULT_URL="${student_url%/}/billing/result"
  fi
}

_resolve_billing_shopper_result_url

EDGE_ZIP="/tmp/billing-edge-${ENV}-$$.zip"
FULFILL_ZIP="/tmp/billing-fulfillment-${ENV}-$$.zip"
EDGE_BUILD="/tmp/billing-edge-build-${ENV}-$$"
FULFILL_BUILD="/tmp/billing-fulfillment-build-${ENV}-$$"
EDGE_KEY="billing-edge-${ENV}-${SUFFIX}.zip"
FULFILL_KEY="billing-fulfillment-${ENV}-${SUFFIX}.zip"
trap 'rm -f "$EDGE_ZIP" "$FULFILL_ZIP"; rm -rf "$EDGE_BUILD" "$FULFILL_BUILD"' EXIT

[[ -d "$EDGE_DIR" ]] || {
  echo "Missing billing edge Lambda: $EDGE_DIR" >&2
  exit 1
}
[[ -f "${FULFILL_DIR}/worker.py" ]] || {
  echo "Missing billing fulfillment Lambda: ${FULFILL_DIR}/worker.py" >&2
  exit 1
}

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

_zip_one_file() {
  local dir="$1"
  local file="$2"
  local out="$3"
  if command -v zip >/dev/null 2>&1; then
    ( cd "$dir" && zip -jq "$out" "$file" )
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
  "$py" - "$dir" "$file" "$out" <<'PY'
import os, sys, zipfile
d, fn, out = sys.argv[1], sys.argv[2], sys.argv[3]
path = os.path.join(d, fn)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(path, fn)
PY
}

rm -rf "$EDGE_BUILD"
mkdir -p "$EDGE_BUILD"
( cd "$EDGE_DIR" && \
  find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
    | xargs -0 -I{} cp --parents '{}' "$EDGE_BUILD" )

REQ_FILE="$EDGE_DIR/requirements.txt"
if [[ -f "$REQ_FILE" ]] && grep -qvE '^\s*($|#)' "$REQ_FILE" 2>/dev/null; then
  echo "Installing billing edge runtime deps into $EDGE_BUILD/_vendor"
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

rm -rf "$FULFILL_BUILD"
mkdir -p "$FULFILL_BUILD"
( cd "$FULFILL_DIR" && \
  find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
    | xargs -0 -I{} cp --parents '{}' "$FULFILL_BUILD" )

FULFILL_REQ="$FULFILL_DIR/requirements.txt"
if [[ -f "$FULFILL_REQ" ]] && grep -qvE '^\s*($|#)' "$FULFILL_REQ" 2>/dev/null; then
  echo "Installing billing fulfillment runtime deps into $FULFILL_BUILD/_vendor"
  pip install \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    -r "$FULFILL_REQ" \
    -t "$FULFILL_BUILD/_vendor"
fi

_zip_dir_recursive "$FULFILL_BUILD" "$FULFILL_ZIP"

echo "Uploading billing edge s3://${ARTIFACT_BUCKET}/${EDGE_KEY}"
aws s3 cp "$EDGE_ZIP" "s3://${ARTIFACT_BUCKET}/${EDGE_KEY}" --region "$REGION"
echo "Uploading billing fulfillment s3://${ARTIFACT_BUCKET}/${FULFILL_KEY}"
aws s3 cp "$FULFILL_ZIP" "s3://${ARTIFACT_BUCKET}/${FULFILL_KEY}" --region "$REGION"

PAYMENT_PROVIDER="${PAYMENT_PROVIDER:-hyperpay}"
HYPERPAY_SECRET_ARN="${HYPERPAY_SECRET_ARN:-}"
HYPERPAY_ACCESS_TOKEN="${HYPERPAY_ACCESS_TOKEN:-}"
HYPERPAY_ENTITY_ID="${HYPERPAY_ENTITY_ID:-}"
HYPERPAY_WEBHOOK_SECRET="${HYPERPAY_WEBHOOK_SECRET:-}"
BILLING_FULFILLMENT_ALERT_EMAIL="${BILLING_FULFILLMENT_ALERT_EMAIL:-}"

# Hydrate HyperPay inline CFN params from streammycourse/hyperpay/{env} when GitHub/SM-only omits inline keys.
if [[ -z "${HYPERPAY_ACCESS_TOKEN}" || -z "${HYPERPAY_ENTITY_ID}" ]]; then
  SM_NAME="streammycourse/hyperpay/${ENV}"
  if aws secretsmanager describe-secret --secret-id "$SM_NAME" --region "$REGION" >/dev/null 2>&1; then
    SM_JSON="$(aws secretsmanager get-secret-value \
      --secret-id "$SM_NAME" \
      --region "$REGION" \
      --query SecretString \
      --output text 2>/dev/null || true)"
    if [[ -n "${SM_JSON}" && "${SM_JSON}" != "None" ]]; then
      if [[ -z "${HYPERPAY_SECRET_ARN}" ]]; then
        HYPERPAY_SECRET_ARN="$(aws secretsmanager describe-secret \
          --secret-id "$SM_NAME" \
          --region "$REGION" \
          --query ARN \
          --output text 2>/dev/null || true)"
      fi
      if command -v python3 >/dev/null 2>&1; then
        PY=python3
      else
        PY=python
      fi
      export SM_JSON
      {
        read -r _token || _token=""
        read -r _entity || _entity=""
        read -r _webhook || _webhook=""
      } < <("$PY" -c 'import json, os; d=json.loads(os.environ["SM_JSON"]); print(d.get("access_token","")); print(d.get("entity_id","")); print(d.get("webhook_secret",""))' 2>/dev/null)
      unset SM_JSON
      if [[ -z "${HYPERPAY_ACCESS_TOKEN}" && -n "${_token}" ]]; then
        HYPERPAY_ACCESS_TOKEN="$_token"
      fi
      if [[ -z "${HYPERPAY_ENTITY_ID}" && -n "${_entity}" ]]; then
        HYPERPAY_ENTITY_ID="$_entity"
      fi
      if [[ -z "${HYPERPAY_WEBHOOK_SECRET}" && -n "${_webhook}" ]]; then
        HYPERPAY_WEBHOOK_SECRET="$_webhook"
      fi
      unset _token _entity _webhook
    fi
  fi
fi

if [[ "$PAYMENT_PROVIDER" != "mock" && "$PAYMENT_PROVIDER" != "hyperpay" ]]; then
  echo "PAYMENT_PROVIDER must be mock or hyperpay, got: $PAYMENT_PROVIDER" >&2
  exit 1
fi

# Fail deploy when HyperPay credentials are empty after GitHub env + SM hydration (mock skips).
if [[ "$PAYMENT_PROVIDER" != "mock" ]]; then
  if [[ -z "${BILLING_SHOPPER_RESULT_URL}" ]]; then
    echo "BILLING_SHOPPER_RESULT_URL is empty; deploy edge hosting first or set StudentSiteUrl output" >&2
    exit 1
  fi
  if [[ -z "${HYPERPAY_ACCESS_TOKEN}" ]]; then
    echo "HYPERPAY_ACCESS_TOKEN is empty after hydration; set GitHub secrets or SM streammycourse/hyperpay/${ENV} with non-empty access_token" >&2
    exit 1
  fi
  if [[ -z "${HYPERPAY_ENTITY_ID}" ]]; then
    echo "HYPERPAY_ENTITY_ID is empty after hydration; set GitHub secrets or SM streammycourse/hyperpay/${ENV} with non-empty entity_id" >&2
    exit 1
  fi
fi

PAYMENTS_TEMPLATE="${TEMPLATE_DIR}/payments-stack.yaml"
if command -v cygpath >/dev/null 2>&1; then
  VALIDATE_BODY_URI="file://$(cygpath -m "$PAYMENTS_TEMPLATE")"
else
  VALIDATE_BODY_URI="file://${PAYMENTS_TEMPLATE}"
fi
aws cloudformation validate-template \
  --template-body "$VALIDATE_BODY_URI" \
  --region "$REGION"

echo "Deploying payments stack: $PAYMENTS_STACK (RdsStackName=$RDS_STACK)"
aws cloudformation deploy \
  --template-file "$PAYMENTS_TEMPLATE" \
  --stack-name "$PAYMENTS_STACK" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
  "Environment=${ENV}" \
  "LambdaCodeS3Bucket=${ARTIFACT_BUCKET}" \
  "BillingEdgeCodeS3Key=${EDGE_KEY}" \
  "BillingFulfillmentCodeS3Key=${FULFILL_KEY}" \
  "RdsStackName=${RDS_STACK}" \
  "PaymentProvider=${PAYMENT_PROVIDER}" \
  "HyperpaySecretArn=${HYPERPAY_SECRET_ARN}" \
  "HyperpayAccessToken=${HYPERPAY_ACCESS_TOKEN}" \
  "HyperpayEntityId=${HYPERPAY_ENTITY_ID}" \
  "HyperpayWebhookSecret=${HYPERPAY_WEBHOOK_SECRET}" \
  "BillingFulfillmentAlertEmail=${BILLING_FULFILLMENT_ALERT_EMAIL}" \
  "CatalogLambdaArn=${CATALOG_LAMBDA_ARN}" \
  "BillingShopperResultUrl=${BILLING_SHOPPER_RESULT_URL}" \
  "CorsAllowOrigin=${CORS}"
