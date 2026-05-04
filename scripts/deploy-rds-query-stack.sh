#!/usr/bin/env bash
# Deploy StreamMyCourse-RdsQuery-<env> (invoke-only operator Lambda for SQL / wipe).
#
# Usage:
#   ./scripts/deploy-rds-query-stack.sh <dev|integ|prod|staging>
#
# Requires: aws CLI, zip, python3 + pip, bash. Build uses Linux manylinux wheels
# for Lambda (same artifact pattern as deploy-rds-stack / schema applier).
#
# Region: AWS_REGION or AWS_DEFAULT_REGION (default eu-west-1).
#
# Optional env for CloudFormation parameters (default false):
#   ALLOW_CATALOG_WIPE=true   — function accepts wipe_catalog invocations
#   ALLOW_MUTATING_SQL=true   — function accepts mutating sql + payload flag

set -euo pipefail

ENV="${1:?Usage: deploy-rds-query-stack.sh <dev|integ|prod|staging>}"
case "$ENV" in
  dev | integ | prod | staging) ;;
  *)
    echo "Environment must be dev, integ, prod, or staging, got: $ENV" >&2
    exit 1
    ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-1}}"
TEMPLATE="${ROOT}/infrastructure/templates/rds-query-stack.yaml"
STACK="StreamMyCourse-RdsQuery-${ENV}"
RDS_STACK="StreamMyCourse-Rds-${ENV}"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE" >&2
  exit 1
fi

if command -v cygpath >/dev/null 2>&1; then
  TEMPLATE_URI="file://$(cygpath -m "$TEMPLATE")"
else
  TEMPLATE_URI="file://${TEMPLATE}"
fi

aws cloudformation validate-template \
  --template-body "$TEMPLATE_URI" \
  --region "$REGION"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
BUCKET="streammycourse-artifacts-${ACCOUNT}-${REGION}"
KEY="rds-query-local-$(date +%s).zip"
ALLOW_CATALOG_WIPE="${ALLOW_CATALOG_WIPE:-false}"
ALLOW_MUTATING_SQL="${ALLOW_MUTATING_SQL:-false}"
STAGE="$(mktemp -d)"
PKG="${STAGE}/pkg"
mkdir -p "$PKG"
cp "${ROOT}/infrastructure/lambda/rds_query/index.py" "$PKG/"
pip install psycopg2-binary==2.9.9 \
  --quiet \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --python-version 3.11 \
  --implementation cp \
  -t "$PKG"
BUNDLE="${STAGE}/bundle.zip"
if command -v zip >/dev/null 2>&1; then
  (cd "$PKG" && zip -rq "$BUNDLE" .)
else
  PYTHON_BIN="${PYTHON:-python3}"
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python"
  fi
  "$PYTHON_BIN" - "$PKG" "$BUNDLE" <<'PY'
import sys, zipfile
from pathlib import Path
pkg, out = Path(sys.argv[1]), Path(sys.argv[2])
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in pkg.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to(pkg))
PY
fi
aws s3 cp "${STAGE}/bundle.zip" "s3://${BUCKET}/${KEY}" --region "$REGION"
rm -rf "$STAGE"
echo "Uploaded query bundle s3://${BUCKET}/${KEY}"

if command -v cygpath >/dev/null 2>&1; then
  TEMPLATE_DEPLOY="$(cygpath -m "$TEMPLATE")"
else
  TEMPLATE_DEPLOY="$TEMPLATE"
fi

aws cloudformation deploy \
  --template-file "$TEMPLATE_DEPLOY" \
  --stack-name "$STACK" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "Environment=${ENV}" \
    "RdsStackName=${RDS_STACK}" \
    "QueryLambdaCodeS3Bucket=${BUCKET}" \
    "QueryLambdaCodeS3Key=${KEY}" \
    "AllowCatalogWipe=${ALLOW_CATALOG_WIPE}" \
    "AllowMutatingSql=${ALLOW_MUTATING_SQL}"

echo "Done. Stack: $STACK  Function: StreamMyCourse-RdsQuery-${ENV}"
echo "Runbook: infrastructure/database/RDS_QUERY_RUNBOOK.md"
