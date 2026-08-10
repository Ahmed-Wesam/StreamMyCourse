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

echo "Syncing master password for ${DB_ID} from ${SECRET_ID} ..."

TMP_JSON="$(mktemp)"
chmod 600 "$TMP_JSON"
trap 'rm -f "$TMP_JSON"' EXIT

aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" \
  --region "$REGION" \
  --query SecretString \
  --output text \
| "$PY" - "$TMP_JSON" "$DB_ID" <<'PY'
import json
import sys

secret_json = sys.stdin.read()
out_path = sys.argv[1]
db_id = sys.argv[2]
password = json.loads(secret_json)["password"]
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(
        {
            "DBInstanceIdentifier": db_id,
            "MasterUserPassword": password,
            "ApplyImmediately": True,
        },
        fh,
    )
PY

aws rds modify-db-instance \
  --cli-input-json "file://${TMP_JSON}" \
  --region "$REGION"

echo "Waiting for RDS instance ${DB_ID} ..."
aws rds wait db-instance-available \
  --db-instance-identifier "$DB_ID" \
  --region "$REGION"

echo "Done. RDS ${DB_ID} password matches ${SECRET_ID}"
