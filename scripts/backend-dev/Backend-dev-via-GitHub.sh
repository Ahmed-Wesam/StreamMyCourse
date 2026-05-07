#!/usr/bin/env bash
# Dispatch **Deploy backend dev only** on GitHub (`.github/workflows/deploy-backend-dev-only.yml`):
# same steps as **Deploy → Backend (dev) — Video + API** — Cognito auth + `deploy-backend.sh dev`.
# Environment **dev** secrets (Google OAuth, etc.) stay on Actions; they cannot be read locally.
#
# Does not run edge, RDS, schema applier, integration tests, SPA deploys, or prod jobs.
#
# Usage:
#   ./scripts/backend-dev/Backend-dev-via-GitHub.sh           # refs current branch
#   ./scripts/backend-dev/Backend-dev-via-GitHub.sh main      # explicit ref

set -euo pipefail
REF="${1:-}"
if [[ -z "$REF" ]]; then
  if git rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
    REF="$(git rev-parse --abbrev-ref HEAD)"
  else
    REF="main"
  fi
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI (https://cli.github.com/) and run: gh auth login" >&2
  exit 1
fi

WORKFLOW="deploy-backend-dev-only.yml"
gh workflow run "$WORKFLOW" --ref "$REF"
echo "Triggered workflow ${WORKFLOW} for ref=$REF — gh run list --workflow ${WORKFLOW}"
