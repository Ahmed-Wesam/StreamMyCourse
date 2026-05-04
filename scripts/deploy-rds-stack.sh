#!/usr/bin/env bash
# Deploy StreamMyCourse-Rds-<env> from your workstation (same steps as CI deploy-rds-* jobs).
#
# Usage:
#   ./scripts/deploy-rds-stack.sh <dev|integ|prod>
#   SKIP_SCHEMA_APPLIER=1 ./scripts/deploy-rds-stack.sh prod   # VPC + RDS only (no applier Lambda)
#
# Requires: aws CLI, zip, python3 + pip, bash. Build uses Linux manylinux wheels for Lambda (same
# as CI); run from Git Bash on Windows or WSL — native Windows Python may not honor --platform.
#
# Region: AWS_REGION or AWS_DEFAULT_REGION (default eu-west-1).

set -euo pipefail

ENV="${1:?Usage: deploy-rds-stack.sh <dev|integ|prod>}"
case "$ENV" in
  dev | integ | prod) ;;
  *)
    echo "Environment must be dev, integ, or prod, got: $ENV" >&2
    exit 1
    ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-1}}"
TEMPLATE="${ROOT}/infrastructure/templates/rds-stack.yaml"
STACK="StreamMyCourse-Rds-${ENV}"
DB_ID="streammycourse-${ENV}"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE" >&2
  exit 1
fi

# Git Bash / MSYS: Windows aws.exe often rejects file:///c/Users/... — use mixed Windows path.
if command -v cygpath >/dev/null 2>&1; then
  TEMPLATE_URI="file://$(cygpath -m "$TEMPLATE")"
else
  TEMPLATE_URI="file://${TEMPLATE}"
fi

aws cloudformation validate-template \
  --template-body "$TEMPLATE_URI" \
  --region "$REGION"

OVERRIDES=("Environment=${ENV}")

if [[ -n "${SKIP_SCHEMA_APPLIER:-}" ]]; then
  echo "SKIP_SCHEMA_APPLIER set: deploying without schema-applier Lambda (empty S3 params)."
  OVERRIDES+=("SchemaApplierCodeS3Bucket=" "SchemaApplierCodeS3Key=")
else
  ACCOUNT="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
  BUCKET="streammycourse-artifacts-${ACCOUNT}-${REGION}"
  KEY="rds-schema-apply-local-$(date +%s).zip"
  STAGE="$(mktemp -d)"
  PKG="${STAGE}/pkg"
  mkdir -p "$PKG"
  cp "${ROOT}/infrastructure/lambda/rds_schema_apply/index.py" "$PKG/"
  cp "${ROOT}/infrastructure/database/migrations/001_initial_schema.sql" "$PKG/schema.sql"
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
  echo "Uploaded schema-applier s3://${BUCKET}/${KEY}"
  OVERRIDES+=("SchemaApplierCodeS3Bucket=${BUCKET}" "SchemaApplierCodeS3Key=${KEY}")
fi

# deploy uses --template-file; pass Windows path when under MSYS so aws.exe can open the file.
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
  --parameter-overrides "${OVERRIDES[@]}"

echo "Waiting for RDS instance ${DB_ID} ..."
aws rds wait db-instance-available \
  --db-instance-identifier "$DB_ID" \
  --region "$REGION"

echo "Done. Stack: $STACK  DB: $DB_ID  Region: $REGION"
