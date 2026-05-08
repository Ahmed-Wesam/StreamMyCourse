#!/usr/bin/env bash
# Run integration tests locally against the deployed dev environment.
# Resolves stack outputs, mints a Cognito JWT, and runs pytest.
#
# Prerequisites:
#   - AWS CLI configured with credentials that can read CloudFormation stacks
#     and call cognito-idp:AdminInitiateAuth on the dev user pool
#   - Dev stacks deployed (streammycourse-api, StreamMyCourse-Video-dev, StreamMyCourse-Auth-dev)
#   - CI Cognito user created via ensure-ci-rds-verify-cognito-user.sh
#
# Password is read from .env.local file (auto-loaded) or environment variable
#
# Usage:
#   ./scripts/run-local-integration-tests.sh             # Uses .env.local — full suite
#   ./scripts/run-local-integration-tests.sh -v          # Full suite, verbose (-v does not shrink scope)
#   ./scripts/run-local-integration-tests.sh -k smoke    # Full tree under tests/integration, keyword filter
#   ./scripts/run-local-integration-tests.sh -v tests/integration/test_publish.py::test_anonymous_get_draft_course_returns_404
#     # Narrow: any arg that looks like tests/integration/... or contains :: selects only those tests (no trailing full-tree path)
#
# Environment variables (all 3 passwords are REQUIRED):
#   LOCAL_COGNITO_USERNAME    - default: ci-rds-verify@noreply.local
#   LOCAL_COGNITO_PASSWORD    - required (the CI user's permanent password)
#   LOCAL_COGNITO_USERNAME_ALT - alternate teacher username (default: ci-rds-verify-2@noreply.local)
#   LOCAL_COGNITO_PASSWORD_ALT - alternate teacher password (required)
#   LOCAL_COGNITO_USERNAME_STUDENT - student username (default: ci-student@noreply.local)
#   LOCAL_COGNITO_PASSWORD_STUDENT - student password (required)
#   AWS_REGION / AWS_DEFAULT_REGION - default: eu-west-1
#   INTEGRATION_EXPECTED_CORS_ORIGIN - optional; if unset, derived from API stack CorsAllowOrigin (first CSV segment)

set +H
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env.local if it exists (for LOCAL_COGNITO_PASSWORD, etc.)
if [[ -f "$REPO_ROOT/.env.local" ]]; then
    # shellcheck source=/dev/null
    set -a
    source "$REPO_ROOT/.env.local"
    set +a
fi

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-1}}"
USERNAME="${LOCAL_COGNITO_USERNAME:-ci-rds-verify@noreply.local}"
PASSWORD="${LOCAL_COGNITO_PASSWORD:-}"
USERNAME_ALT="${LOCAL_COGNITO_USERNAME_ALT:-ci-rds-verify-2@noreply.local}"
PASSWORD_ALT="${LOCAL_COGNITO_PASSWORD_ALT:-}"
USERNAME_STUDENT="${LOCAL_COGNITO_USERNAME_STUDENT:-ci-student@noreply.local}"
PASSWORD_STUDENT="${LOCAL_COGNITO_PASSWORD_STUDENT:-}"
SKIP_JWT="${SKIP_JWT:-}"

# Stack names (dev defaults)
API_STACK="streammycourse-api"
VIDEO_STACK="StreamMyCourse-Video-dev"
AUTH_STACK="StreamMyCourse-Auth-dev"

# Collect extra args for pytest
PYTEST_ARGS=("$@")

function log_info() {
    echo "[local-integ] $1"
}

function log_error() {
    echo "[local-integ] ERROR: $1" >&2
}

function require_command() {
    if ! command -v "$1" &>/dev/null; then
        log_error "Required command '$1' not found on PATH. Install it and retry."
        exit 1
    fi
}

require_command "aws"
require_command "python"

# --- Resolve stack outputs -------------------------------------------------

log_info "Resolving stack outputs (region: $REGION)..."

API_BASE_URL="$(aws cloudformation describe-stacks \
    --stack-name "$API_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
    --output text 2>/dev/null || true)"

if [[ -z "$API_BASE_URL" || "$API_BASE_URL" == "None" ]]; then
    log_error "Could not resolve ApiEndpoint from stack $API_STACK"
    exit 1
fi

VIDEO_BUCKET="$(aws cloudformation describe-stacks \
    --stack-name "$VIDEO_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
    --output text 2>/dev/null || true)"

if [[ -z "$VIDEO_BUCKET" || "$VIDEO_BUCKET" == "None" ]]; then
    log_error "Could not resolve BucketName from stack $VIDEO_STACK"
    exit 1
fi

# First allowlisted origin for CORS assertions (matches deploy-backend integration job).
if [[ -z "${INTEGRATION_EXPECTED_CORS_ORIGIN:-}" ]]; then
    CORS_CSV="$(aws cloudformation describe-stacks \
        --stack-name "$API_STACK" \
        --region "$REGION" \
        --query "Stacks[0].Parameters[?ParameterKey=='CorsAllowOrigin'].ParameterValue" \
        --output text 2>/dev/null || true)"
    FIRST_CORS_ORIGIN="${CORS_CSV%%,*}"
    FIRST_CORS_ORIGIN="${FIRST_CORS_ORIGIN#"${FIRST_CORS_ORIGIN%%[![:space:]]*}"}"
    FIRST_CORS_ORIGIN="${FIRST_CORS_ORIGIN%"${FIRST_CORS_ORIGIN##*[![:space:]]}"}"
    if [[ -z "$FIRST_CORS_ORIGIN" || "$FIRST_CORS_ORIGIN" == "None" ]]; then
        FIRST_CORS_ORIGIN="http://localhost:5173"
    fi
    export INTEGRATION_EXPECTED_CORS_ORIGIN="$FIRST_CORS_ORIGIN"
fi

log_info "API endpoint: $API_BASE_URL"
log_info "Video bucket: $VIDEO_BUCKET"
log_info "Expected CORS first origin: $INTEGRATION_EXPECTED_CORS_ORIGIN"

# --- Mint Cognito JWT (required) -------------------------------------------

export INTEGRATION_COGNITO_JWT=""
export INTEGRATION_COGNITO_JWT_ALT=""
export INTEGRATION_COGNITO_JWT_STUDENT=""

if [[ "$SKIP_JWT" == "1" ]]; then
    log_error "SKIP_JWT=1 is not supported - all 3 JWTs are required for integration tests"
    exit 1
fi

if [[ -z "$PASSWORD" ]]; then
    log_error "LOCAL_COGNITO_PASSWORD is required (primary teacher)"
    exit 1
fi

if [[ -z "$PASSWORD_ALT" ]]; then
    log_error "LOCAL_COGNITO_PASSWORD_ALT is required (alternate teacher)"
    exit 1
fi

if [[ -z "$PASSWORD_STUDENT" ]]; then
    log_error "LOCAL_COGNITO_PASSWORD_STUDENT is required (student)"
    exit 1
fi

log_info "Minting Cognito JWT for user: $USERNAME"

USER_POOL_ID="$(aws cloudformation describe-stacks \
        --stack-name "$AUTH_STACK" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
        --output text 2>/dev/null || true)"

CLIENT_ID="$(aws cloudformation describe-stacks \
        --stack-name "$AUTH_STACK" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='TeacherUserPoolClientId'].OutputValue" \
        --output text 2>/dev/null || true)"

if [[ -z "$USER_POOL_ID" || "$USER_POOL_ID" == "None" || -z "$CLIENT_ID" || "$CLIENT_ID" == "None" ]]; then
    log_error "Could not resolve UserPoolId or TeacherUserPoolClientId from stack $AUTH_STACK"
    exit 1
fi

# Build auth input JSON inline (avoids temp file path issues on Windows bash/WSL)
# Escape password for JSON (handle " and \ characters)
PASSWORD_ESCAPED="${PASSWORD//\\/\\\\}"
PASSWORD_ESCAPED="${PASSWORD_ESCAPED//\"/\\\"}"
AUTH_JSON="{\"UserPoolId\":\"$USER_POOL_ID\",\"ClientId\":\"$CLIENT_ID\",\"AuthFlow\":\"ADMIN_USER_PASSWORD_AUTH\",\"AuthParameters\":{\"USERNAME\":\"$USERNAME\",\"PASSWORD\":\"$PASSWORD_ESCAPED\"}}"

TOKEN="$(aws cognito-idp admin-initiate-auth \
        --cli-input-json "$AUTH_JSON" \
        --region "$REGION" \
        --query 'AuthenticationResult.IdToken' \
        --output text 2>/dev/null || true)"

if [[ -n "$TOKEN" && "$TOKEN" != "None" ]]; then
    export INTEGRATION_COGNITO_JWT="$TOKEN"
    log_info "JWT minted successfully (primary teacher)"
else
    log_error "Failed to mint Cognito JWT - check your LOCAL_COGNITO_PASSWORD"
    exit 1
fi

# --- Mint alternate teacher JWT (required) -------------------------------
log_info "Minting Cognito JWT for alternate teacher: $USERNAME_ALT"

PASSWORD_ALT_ESCAPED="${PASSWORD_ALT//\\/\\\\}"
PASSWORD_ALT_ESCAPED="${PASSWORD_ALT_ESCAPED//\"/\\\"}"
AUTH_JSON_ALT="{\"UserPoolId\":\"$USER_POOL_ID\",\"ClientId\":\"$CLIENT_ID\",\"AuthFlow\":\"ADMIN_USER_PASSWORD_AUTH\",\"AuthParameters\":{\"USERNAME\":\"$USERNAME_ALT\",\"PASSWORD\":\"$PASSWORD_ALT_ESCAPED\"}}"

TOKEN_ALT="$(aws cognito-idp admin-initiate-auth \
        --cli-input-json "$AUTH_JSON_ALT" \
        --region "$REGION" \
        --query 'AuthenticationResult.IdToken' \
        --output text 2>/dev/null || true)"

if [[ -n "$TOKEN_ALT" && "$TOKEN_ALT" != "None" ]]; then
    export INTEGRATION_COGNITO_JWT_ALT="$TOKEN_ALT"
    log_info "JWT minted successfully (alternate teacher)"
else
    log_error "Failed to mint Cognito JWT for alternate teacher - check your LOCAL_COGNITO_PASSWORD_ALT"
    exit 1
fi

# --- Mint student JWT (required) -----------------------------------------
log_info "Minting Cognito JWT for student: $USERNAME_STUDENT"

PASSWORD_STUDENT_ESCAPED="${PASSWORD_STUDENT//\\/\\\\}"
PASSWORD_STUDENT_ESCAPED="${PASSWORD_STUDENT_ESCAPED//\"/\\\"}"
AUTH_JSON_STUDENT="{\"UserPoolId\":\"$USER_POOL_ID\",\"ClientId\":\"$CLIENT_ID\",\"AuthFlow\":\"ADMIN_USER_PASSWORD_AUTH\",\"AuthParameters\":{\"USERNAME\":\"$USERNAME_STUDENT\",\"PASSWORD\":\"$PASSWORD_STUDENT_ESCAPED\"}}"

TOKEN_STUDENT="$(aws cognito-idp admin-initiate-auth \
        --cli-input-json "$AUTH_JSON_STUDENT" \
        --region "$REGION" \
        --query 'AuthenticationResult.IdToken' \
        --output text 2>/dev/null || true)"

if [[ -n "$TOKEN_STUDENT" && "$TOKEN_STUDENT" != "None" ]]; then
    export INTEGRATION_COGNITO_JWT_STUDENT="$TOKEN_STUDENT"
    log_info "JWT minted successfully (student)"
else
    log_error "Failed to mint Cognito JWT for student - check your LOCAL_COGNITO_PASSWORD_STUDENT"
    exit 1
fi

# --- Export environment and run pytest ----------------------------------------

export INTEGRATION_API_BASE_URL="${API_BASE_URL%/}"  # strip trailing slash
export INTEGRATION_VIDEO_BUCKET="$VIDEO_BUCKET"
export INTEGRATION_AWS_REGION="$REGION"

log_info "Running pytest..."

cd "$REPO_ROOT"

# Install dependencies if needed
if ! python -c "import pytest, httpx, boto3" 2>/dev/null; then
    log_info "Installing test dependencies..."
    pip install -q -r tests/integration/requirements.txt
fi

# Default is always the full integration tree. Pytest options alone (-v, -k, -m, …) still run
# tests/integration. Only when the caller passes an explicit path under tests/integration/ or a
# node id (contains ::) do we omit the trailing package path so selection stays narrow.
has_explicit_target=false
for a in "${PYTEST_ARGS[@]}"; do
    case "$a" in
    tests/integration/* | */tests/integration/* | ./*tests/integration/*)
        has_explicit_target=true
        break
        ;;
    *::*)
        has_explicit_target=true
        break
        ;;
    esac
done
if [[ "$has_explicit_target" == true ]]; then
    python -m pytest "${PYTEST_ARGS[@]}"
else
    python -m pytest "${PYTEST_ARGS[@]}" tests/integration
fi
