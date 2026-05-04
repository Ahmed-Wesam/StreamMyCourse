#!/usr/bin/env bash
# Apply version-controlled IAM inline policies to an existing GitHub Actions OIDC deploy role.
# Prefer ./scripts/deploy-github-iam-stack.sh for full role + OIDC bootstrap (CloudFormation).
# Run locally (with admin IAM credentials) BEFORE pushing workflow or policy changes that
# need new permissions — otherwise Deploy can fail mid-pipeline (e.g. ACM in us-east-1).
#
# Source of truth: infrastructure/iam-policy-github-deploy-backend.json
#                 + infrastructure/iam-policy-github-deploy-web.json
#
# Usage:
#   ./scripts/apply-github-deploy-role-policies.sh
#   GITHUB_DEPLOY_ROLE_NAME=my-role ./scripts/apply-github-deploy-role-policies.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE_NAME="${GITHUB_DEPLOY_ROLE_NAME:-StreamMyCourseGitHubDeployWeb}"

BACKEND_DOC="${ROOT}/infrastructure/iam-policy-github-deploy-backend.json"
WEB_DOC="${ROOT}/infrastructure/iam-policy-github-deploy-web.json"

for f in "$BACKEND_DOC" "$WEB_DOC"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing policy file: $f" >&2
    exit 1
  fi
done

echo "Applying inline policies to IAM role: $ROLE_NAME"
aws iam get-role --role-name "$ROLE_NAME" >/dev/null

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name StreamMyCourseGitHubDeployBackend \
  --policy-document "file://${BACKEND_DOC}"

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name StreamMyCourseGitHubDeployWeb \
  --policy-document "file://${WEB_DOC}"

echo "[OK] StreamMyCourseGitHubDeployBackend + StreamMyCourseGitHubDeployWeb updated on $ROLE_NAME"
