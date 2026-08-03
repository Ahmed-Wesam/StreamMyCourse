#!/usr/bin/env bash
# Set given_name, family_name, and email on CI/integration Cognito users before JWT mint.
# Requires a password per user (skips users whose password env is empty).
#
# Environment (mirrors deploy-backend integration mint steps):
#   COGNITO_TEST_PASSWORD / COGNITO_TEST_USERNAME — primary teacher
#   COGNITO_TEST_PASSWORD_ALT / COGNITO_TEST_USERNAME_ALT — alt teacher (optional)
#   COGNITO_TEST_PASSWORD_STUDENT / COGNITO_TEST_USERNAME_STUDENT — student (optional)
#   CI_RDS_VERIFY_AUTH_STACK — default StreamMyCourse-Auth-prod

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENSURE="${REPO_ROOT}/scripts/ensure-ci-rds-verify-cognito-user.sh"

ensure_one() {
  local role="$1"
  local username="$2"
  local password="${3:-}"
  if [[ -z "$password" ]]; then
    return 0
  fi
  echo "Ensuring playback profile for ${username} (${role})"
  CI_RDS_VERIFY_PASSWORD="$password" \
    CI_RDS_VERIFY_AUTH_STACK="${CI_RDS_VERIFY_AUTH_STACK:-StreamMyCourse-Auth-prod}" \
    "$ENSURE" --role "$role" --username "$username"
}

ensure_one teacher "${COGNITO_TEST_USERNAME:-ci-rds-verify@noreply.local}" "${COGNITO_TEST_PASSWORD:-}"
ensure_one teacher "${COGNITO_TEST_USERNAME_ALT:-ci-rds-verify-2@noreply.local}" "${COGNITO_TEST_PASSWORD_ALT:-}"
ensure_one student "${COGNITO_TEST_USERNAME_STUDENT:-ci-student@noreply.local}" "${COGNITO_TEST_PASSWORD_STUDENT:-}"
