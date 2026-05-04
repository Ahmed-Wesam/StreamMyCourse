#!/usr/bin/env bash
# Create or update the dedicated CI teacher user for Verify dev/prod RDS (or local RDS path tests).
# Requires AWS credentials with cognito-idp admin APIs on the target pool (default dev stack).
#
# Usage:
#   ./scripts/ensure-ci-rds-verify-cognito-user.sh
#   CI_RDS_VERIFY_PASSWORD='your-strong-password' ./scripts/ensure-ci-rds-verify-cognito-user.sh
#
# Environment:
#   AWS_REGION / AWS_DEFAULT_REGION — default eu-west-1
#   CI_RDS_VERIFY_USERNAME — default ci-rds-verify@noreply.local
#   CI_RDS_VERIFY_PASSWORD — permanent password (required for new users; optional to only set role)

set -euo pipefail

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-1}}"
USERNAME="${CI_RDS_VERIFY_USERNAME:-ci-rds-verify@noreply.local}"
STACK="${CI_RDS_VERIFY_AUTH_STACK:-StreamMyCourse-Auth-dev}"

POOL_ID="$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text)"

if [[ -z "$POOL_ID" || "$POOL_ID" == "None" ]]; then
  echo "Failed to read UserPoolId from stack $STACK in $REGION" >&2
  exit 1
fi

if aws cognito-idp admin-get-user --user-pool-id "$POOL_ID" --username "$USERNAME" --region "$REGION" &>/dev/null; then
  echo "User already exists: $USERNAME"
else
  echo "Creating user $USERNAME in pool $POOL_ID"
  TMP_PASS="${CI_RDS_VERIFY_TEMP_PASSWORD:-TempPass123!ChangeMe}"
  aws cognito-idp admin-create-user \
    --user-pool-id "$POOL_ID" \
    --username "$USERNAME" \
    --temporary-password "$TMP_PASS" \
    --message-action SUPPRESS \
    --region "$REGION"
fi

if [[ -n "${CI_RDS_VERIFY_PASSWORD:-}" ]]; then
  echo "Setting permanent password for $USERNAME"
  aws cognito-idp admin-set-user-password \
    --user-pool-id "$POOL_ID" \
    --username "$USERNAME" \
    --password "$CI_RDS_VERIFY_PASSWORD" \
    --permanent \
    --region "$REGION"
else
  echo "CI_RDS_VERIFY_PASSWORD not set; skipping admin-set-user-password (set it to rotate password)." >&2
fi

echo "Ensuring custom:role=teacher"
aws cognito-idp admin-update-user-attributes \
  --user-pool-id "$POOL_ID" \
  --username "$USERNAME" \
  --user-attributes Name=custom:role,Value=teacher \
  --region "$REGION"

echo "Done. Store the same password in GitHub secret COGNITO_RDS_VERIFY_TEST_PASSWORD on the"
echo "GitHub Environment that matches this stack (dev for *-Auth-dev, prod for *-Auth-prod)."
