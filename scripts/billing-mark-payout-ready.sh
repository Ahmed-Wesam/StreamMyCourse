#!/usr/bin/env bash
# W4-F1: thin wrapper — set teacher_merchant_accounts.payout_ready for checklist UI only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${1:-}" ]]; then
  export DEPLOYMENT_ENVIRONMENT="${1}"
fi

if [[ -z "${DEPLOYMENT_ENVIRONMENT:-}" ]]; then
  echo "billing-mark-payout-ready: DEPLOYMENT_ENVIRONMENT unset (pass dev|prod as arg or env)" >&2
  exit 1
fi

PY=""
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "billing-mark-payout-ready: python not found" >&2
  exit 1
fi

if ! "$PY" -c "import psycopg2" 2>/dev/null; then
  echo "billing-mark-payout-ready: psycopg2 not installed (pip install psycopg2-binary)" >&2
  exit 1
fi

exec "$PY" "$ROOT/scripts/billing_mark_payout_ready.py"
