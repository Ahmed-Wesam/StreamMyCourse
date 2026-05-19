#!/usr/bin/env bash
# Deploy StreamMyCourse-Payments-{env}: billing edge + fulfillment SQS/Lambda (WS2).
set -euo pipefail

ENV="${1:?Usage: deploy-payments.sh <dev|prod> <region> <artifact_bucket> <suffix>}"
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
EDGE_DIR="$ROOT/infrastructure/lambda/billing_edge"
FULFILL_DIR="$ROOT/infrastructure/lambda/billing_fulfillment"

PAYMENTS_STACK="StreamMyCourse-Payments-${ENV}"
RDS_STACK="${RDS_STACK_NAME:-StreamMyCourse-Rds-${ENV}}"

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

PAYMENT_PROVIDER="${PAYMENT_PROVIDER:-}"
PAYTABS_API_DOMAIN="${PAYTABS_API_DOMAIN:-secure-jordan.paytabs.com}"
PAYTABS_PROFILE_ID="${PAYTABS_PROFILE_ID:-}"
PAYTABS_SERVER_KEY="${PAYTABS_SERVER_KEY:-}"
PAYTABS_SECRET_ARN="${PAYTABS_SECRET_ARN:-}"
PAYTABS_USE_MOCK="${PAYTABS_USE_MOCK:-false}"
BILLING_FULFILLMENT_ALERT_EMAIL="${BILLING_FULFILLMENT_ALERT_EMAIL:-}"

# Hydrate inline CFN params from streammycourse/paytabs/{env} when GitHub/SM-only (prod) omits inline keys.
if [[ -z "${PAYTABS_SERVER_KEY}" || -z "${PAYTABS_PROFILE_ID}" ]]; then
  SM_NAME="streammycourse/paytabs/${ENV}"
  if aws secretsmanager describe-secret --secret-id "$SM_NAME" --region "$REGION" >/dev/null 2>&1; then
    SM_JSON="$(aws secretsmanager get-secret-value \
      --secret-id "$SM_NAME" \
      --region "$REGION" \
      --query SecretString \
      --output text 2>/dev/null || true)"
    if [[ -n "${SM_JSON}" && "${SM_JSON}" != "None" ]]; then
      if [[ -z "${PAYTABS_SECRET_ARN}" ]]; then
        PAYTABS_SECRET_ARN="$(aws secretsmanager describe-secret \
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
        read -r _sk || _sk=""
        read -r _pid || _pid=""
        read -r _dom || _dom=""
      } < <("$PY" -c 'import json, os; d=json.loads(os.environ["SM_JSON"]); print(d.get("server_key","")); print(d.get("profile_id","")); print(d.get("api_domain",""))' 2>/dev/null)
      unset SM_JSON
      if [[ -z "${PAYTABS_SERVER_KEY}" && -n "${_sk}" ]]; then
        PAYTABS_SERVER_KEY="$_sk"
      fi
      if [[ -z "${PAYTABS_PROFILE_ID}" && -n "${_pid}" ]]; then
        PAYTABS_PROFILE_ID="$_pid"
      fi
      if [[ -n "${_dom}" ]]; then
        PAYTABS_API_DOMAIN="$_dom"
      fi
      unset _sk _pid _dom
    fi
  fi
fi
if [[ "$PAYTABS_USE_MOCK" != "true" && "$PAYTABS_USE_MOCK" != "false" ]]; then
  echo "PAYTABS_USE_MOCK must be true or false, got: $PAYTABS_USE_MOCK" >&2
  exit 1
fi

# WS3: fail deploy when server_key is empty after GitHub env + SM hydration (dev and prod).
# Non-empty placeholder values in streammycourse/paytabs/{env} (or GitHub dev PAYTABS_SERVER_KEY)
# satisfy this guard until live PayTabs keys are configured.
if [[ -z "${PAYTABS_SERVER_KEY}" ]]; then
  echo "PAYTABS_SERVER_KEY is empty after hydration; set GitHub secret or SM streammycourse/paytabs/${ENV} with non-empty server_key" >&2
  exit 1
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
  "PaytabsApiDomain=${PAYTABS_API_DOMAIN}" \
  "PaytabsProfileId=${PAYTABS_PROFILE_ID}" \
  "PaytabsServerKey=${PAYTABS_SERVER_KEY}" \
  "PaytabsSecretArn=${PAYTABS_SECRET_ARN}" \
  "PaytabsUseMock=${PAYTABS_USE_MOCK}" \
  "BillingFulfillmentAlertEmail=${BILLING_FULFILLMENT_ALERT_EMAIL}"

# W4-P4: sync teacher_merchant_accounts when teacher sub is configured (skip if RDS unreachable).
if [[ -n "${BILLING_TEACHER_SUB:-}" ]]; then
  export DEPLOYMENT_ENVIRONMENT="${ENV}"
  bash "${ROOT}/scripts/billing-sync-merchant-account.sh" "${ENV}"
fi
