#!/usr/bin/env bash
# W4-P4: thin wrapper — upsert teacher_merchant_accounts when RDS is reachable.
# Requires psycopg2-binary on the runner (tests/unit/requirements.txt / pip install).
# Skips with exit 0 when RDS is not reachable (typical GitHub Actions without VPC).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${BILLING_TEACHER_SUB:-}" ]]; then
  echo "billing-sync-merchant-account: BILLING_TEACHER_SUB unset; skipping"
  exit 0
fi

if [[ -n "${1:-}" ]]; then
  export DEPLOYMENT_ENVIRONMENT="${1}"
fi

PY=""
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "billing-sync-merchant-account: python not found; skipping"
  exit 0
fi

if ! "$PY" -c "import psycopg2" 2>/dev/null; then
  echo "billing-sync-merchant-account: psycopg2 not installed; skipping (pip install psycopg2-binary)"
  exit 0
fi

exec "$PY" "$ROOT/scripts/billing_sync_merchant_account.py"
