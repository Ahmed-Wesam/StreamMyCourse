#!/usr/bin/env bash
# Create or update the dedicated CI user for Verify prod RDS (or local RDS path tests).
# Requires AWS credentials with cognito-idp admin APIs on the target pool (default prod stack).
#
# Usage:
#   ./scripts/ensure-ci-rds-verify-cognito-user.sh
#   ./scripts/ensure-ci-rds-verify-cognito-user.sh --role student --username student-test@noreply.local
#   CI_RDS_VERIFY_PASSWORD='your-strong-password' ./scripts/ensure-ci-rds-verify-cognito-user.sh
#
# Options:
#   --role ROLE            User role: teacher or student (default: teacher)
#   --username USERNAME    User email/username (default: ci-rds-verify@noreply.local)
#   --help                 Show this help message
#
# Environment:
#   AWS_REGION / AWS_DEFAULT_REGION — default eu-west-1
#   CI_RDS_VERIFY_ROLE — default teacher (can be overridden by --role)
#   CI_RDS_VERIFY_USERNAME — default ci-rds-verify@noreply.local (can be overridden by --username)
#   CI_RDS_VERIFY_PASSWORD — permanent password (required for new users; optional to only set role)
#
# Sets custom:role plus given_name, family_name, and email (CI users; playback needs at least one name part + email).

set -euo pipefail

# Parse CLI arguments
ROLE=""
USERNAME_CLI=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      if [[ -n "${2:-}" && ! "${2:-}" =~ ^-- ]]; then
        ROLE="$2"
        shift 2
      else
        echo "Error: --role requires a value (teacher or student)" >&2
        exit 1
      fi
      ;;
    --username)
      if [[ -n "${2:-}" && ! "${2:-}" =~ ^-- ]]; then
        USERNAME_CLI="$2"
        shift 2
      else
        echo "Error: --username requires a value" >&2
        exit 1
      fi
      ;;
    --help|-h)
      sed -n '/^#/,/^[^#]/p' "$0" | sed '/^[^#]/d' | sed 's/^# //' | sed 's/^#//' | head -20
      exit 0
      ;;
    *)
      echo "Error: Unknown option: $1" >&2
      echo "Usage: $0 [--role ROLE] [--username USERNAME] [--help]" >&2
      exit 1
      ;;
  esac
done

# Apply priority: CLI args > env vars > defaults
ROLE="${ROLE:-${CI_RDS_VERIFY_ROLE:-teacher}}"
USERNAME="${USERNAME_CLI:-${CI_RDS_VERIFY_USERNAME:-ci-rds-verify@noreply.local}}"

# Validate role
if [[ "$ROLE" != "teacher" && "$ROLE" != "student" ]]; then
  echo "Error: ROLE must be either 'teacher' or 'student', got: $ROLE" >&2
  exit 1
fi

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-1}}"
STACK="${CI_RDS_VERIFY_AUTH_STACK:-StreamMyCourse-Auth-prod}"

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

echo "Ensuring custom:role=$ROLE and playback watermark profile (given_name, family_name, email)"
if [[ "$ROLE" == "student" ]]; then
  GIVEN_NAME="CI"
  FAMILY_NAME="Student"
else
  GIVEN_NAME="CI"
  FAMILY_NAME="Teacher"
fi
aws cognito-idp admin-update-user-attributes \
  --user-pool-id "$POOL_ID" \
  --username "$USERNAME" \
  --user-attributes \
    "Name=email,Value=$USERNAME" \
    "Name=email_verified,Value=true" \
    "Name=given_name,Value=$GIVEN_NAME" \
    "Name=family_name,Value=$FAMILY_NAME" \
    "Name=custom:role,Value=$ROLE" \
  --region "$REGION"

echo "Done. Store the same password in GitHub secret COGNITO_RDS_VERIFY_TEST_PASSWORD on the"
echo "GitHub Environment that matches this stack (prod for *-Auth-prod)."
