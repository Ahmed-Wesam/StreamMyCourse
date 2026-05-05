#!/usr/bin/env bash
# Apply version-controlled IAM inline policies to an existing GitHub Actions OIDC deploy role.
# Prefer ./scripts/deploy-github-iam-stack.sh for full role + OIDC bootstrap (CloudFormation).
# Run locally (with admin IAM credentials) BEFORE pushing workflow or policy changes that
# need new permissions — otherwise Deploy can fail mid-pipeline (e.g. ACM in us-east-1).
#
# Policy JSON uses YOUR_AWS_ACCOUNT_ID in ARNs; this script replaces it with the account id
# from aws sts get-caller-identity before iam put-role-policy (raw repo JSON is not valid IAM).
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

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
if [[ -z "$ACCOUNT_ID" ]]; then
  echo "Could not resolve AWS account id (sts get-caller-identity)" >&2
  exit 1
fi

TMP_BACKEND="$(mktemp)"
TMP_WEB="$(mktemp)"
trap 'rm -f "$TMP_BACKEND" "$TMP_WEB"' EXIT

sed "s/YOUR_AWS_ACCOUNT_ID/${ACCOUNT_ID}/g" "$BACKEND_DOC" >"$TMP_BACKEND"
sed "s/YOUR_AWS_ACCOUNT_ID/${ACCOUNT_ID}/g" "$WEB_DOC" >"$TMP_WEB"

echo "Applying inline policies to IAM role: $ROLE_NAME (substituting YOUR_AWS_ACCOUNT_ID -> $ACCOUNT_ID)"
aws iam get-role --role-name "$ROLE_NAME" >/dev/null

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name StreamMyCourseGitHubDeployBackend \
  --policy-document "file://${TMP_BACKEND}"

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name StreamMyCourseGitHubDeployWeb \
  --policy-document "file://${TMP_WEB}"

echo "[OK] StreamMyCourseGitHubDeployBackend + StreamMyCourseGitHubDeployWeb updated on $ROLE_NAME"
