#!/usr/bin/env bash
# Apply the Secrets Manager RDS password to the instance after snapshot restore.
#
# Snapshot restores retain the snapshot's master password; the stack's DbSecret
# may hold a different generated password. Run this after deploy-rds-stack.sh
# with RESTORE_DB_SNAPSHOT_IDENTIFIER so Lambda and operators use the same secret.
#
# Usage:
#   ./scripts/sync-rds-secret-after-restore.sh prod
#
# Region: AWS_REGION or AWS_DEFAULT_REGION (default eu-west-1).

set -euo pipefail

ENV="${1:?Usage: sync-rds-secret-after-restore.sh <prod>}"
case "$ENV" in
  prod) ;;
  *)
    echo "Environment must be prod, got: $ENV" >&2
    exit 1
    ;;
esac

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-1}}"
DB_ID="streammycourse-${ENV}"
SECRET_ID="streammycourse/${ENV}/rds-credentials"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

SECRET_JSON="$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" \
  --region "$REGION" \
  --query SecretString \
  --output text)"

PASSWORD="$("$PY" -c 'import json, sys; print(json.load(sys.stdin)["password"])' <<<"$SECRET_JSON")"

echo "Syncing master password for ${DB_ID} from ${SECRET_ID} ..."

aws rds modify-db-instance \
  --db-instance-identifier "$DB_ID" \
  --master-user-password "$PASSWORD" \
  --apply-immediately \
  --region "$REGION"

echo "Waiting for RDS instance ${DB_ID} ..."
aws rds wait db-instance-available \
  --db-instance-identifier "$DB_ID" \
  --region "$REGION"

echo "Done. RDS ${DB_ID} password matches ${SECRET_ID}"
