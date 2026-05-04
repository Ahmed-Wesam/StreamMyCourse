#!/usr/bin/env bash
# Deploy the GitHub OIDC deploy IAM stack (CloudFormation). NOT used by GitHub Actions — run locally
# with admin credentials when bootstrapping or when github-deploy-role-stack.yaml changes.
#
# Usage (repo root):
#   ./scripts/deploy-github-iam-stack.sh
#   GITHUB_IAM_STACK_NAME=my-stack ./scripts/deploy-github-iam-stack.sh
#
# If the account already has the GitHub OIDC provider, pass its ARN (see infrastructure/README.md):
#   ./scripts/deploy-github-iam-stack.sh --parameter-overrides \
#     ExistingGithubOidcProviderArn=arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK_NAME="${GITHUB_IAM_STACK_NAME:-StreamMyCourse-GitHubDeployIam}"
TEMPLATE="${ROOT}/infrastructure/templates/github-deploy-role-stack.yaml"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing template: $TEMPLATE" >&2
  exit 1
fi

echo "Deploying stack: $STACK_NAME"
if ! aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE" \
  --capabilities CAPABILITY_NAMED_IAM \
  "$@"; then
  echo "[ERROR] aws cloudformation deploy failed" >&2
  exit 1
fi

echo "[OK] Stack deployed. Role ARN:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='GitHubDeployRoleArn'].OutputValue" \
  --output text
