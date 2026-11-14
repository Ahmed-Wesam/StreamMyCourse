#!/usr/bin/env bash
# Deploy dev stage stacks only (DSQL, schema, auth, S3 video bucket, API).
# Must not call deploy-backend.sh or prod-only stacks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT/infrastructure/templates"
LAMBDA_DIR="$ROOT/infrastructure/lambda/catalog"
AUTH_LAMBDA_DIR="$ROOT/infrastructure/lambda/catalog_token_authorizer"
PYTHON="${PYTHON:-python3}"

_refuse_dev() {
  "$PYTHON" -c "import sys; sys.path.insert(0, '${ROOT}/scripts'); from dev_stage import refuse_unless_dev; refuse_unless_dev(sys.argv[1])" "$1"
}

_run_dev_stage_python() {
  "$PYTHON" "$ROOT/scripts/dev_stage.py" "$@"
}

ENV="${1:?Usage: deploy-dev.sh dev <dsql|schema|auth|video|api>}"
SUB="${2:?Usage: deploy-dev.sh dev <dsql|schema|auth|video|api>}"
_refuse_dev "$ENV"

REGION="${AWS_REGION:-eu-west-1}"
DSQL_STACK="StreamMyCourse-Dsql-dev"
AUTH_STACK="StreamMyCourse-Auth-dev"
API_STACK="StreamMyCourse-Api-dev"
VIDEO_STACK="StreamMyCourse-DevVideo-dev"
PROD_DSQL_STACK="StreamMyCourse-Dsql-prod"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
ARTIFACT_BUCKET="streammycourse-artifacts-${ACCOUNT}-${REGION}"

SUFFIX="${LAMBDA_CODE_SUFFIX:-}"
if [[ -z "$SUFFIX" ]] && [[ -n "${GITHUB_SHA:-}" ]]; then
  SUFFIX="${GITHUB_SHA:0:12}"
fi
if [[ -z "$SUFFIX" ]]; then
  if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
    SUFFIX="$(git -C "$ROOT" rev-parse HEAD | cut -c1-12)"
  else
    SUFFIX="$(date +%s)"
  fi
fi
ZIP_KEY="catalog-dev-${SUFFIX}.zip"
AUTH_ZIP_KEY="catalog-token-authorizer-dev-${SUFFIX}.zip"

_dsql_dev_outputs() {
  DSQL_ENDPOINT="$(aws cloudformation describe-stacks \
    --stack-name "$DSQL_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='Endpoint'].OutputValue" \
    --output text)"
  DSQL_CLUSTER_ARN="$(aws cloudformation describe-stacks \
    --stack-name "$DSQL_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='ResourceArn'].OutputValue" \
    --output text)"
  if [[ -z "$DSQL_ENDPOINT" || "$DSQL_ENDPOINT" == "None" || -z "$DSQL_CLUSTER_ARN" || "$DSQL_CLUSTER_ARN" == "None" ]]; then
    echo "Missing DSQL outputs on $DSQL_STACK" >&2
    exit 1
  fi
  export DSQL_ENDPOINT DSQL_CLUSTER_ARN
  "$PYTHON" -c "
import sys
sys.path.insert(0, '${ROOT}/scripts')
from dev_stage import assert_not_prod_cluster
assert_not_prod_cluster('${DSQL_ENDPOINT}')
assert_not_prod_cluster('${DSQL_CLUSTER_ARN}')
"
}

_assert_dsql_differs_from_prod() {
  if aws cloudformation describe-stacks --stack-name "$PROD_DSQL_STACK" --region "$REGION" &>/dev/null; then
    PROD_ENDPOINT="$(aws cloudformation describe-stacks \
      --stack-name "$PROD_DSQL_STACK" \
      --region "$REGION" \
      --query "Stacks[0].Outputs[?OutputKey=='Endpoint'].OutputValue" \
      --output text)"
    if [[ -n "$PROD_ENDPOINT" && "$PROD_ENDPOINT" != "None" ]]; then
      "$PYTHON" -c "
import sys
sys.path.insert(0, '${ROOT}/scripts')
from dev_stage import assert_endpoints_differ
assert_endpoints_differ('${DSQL_ENDPOINT}', '${PROD_ENDPOINT}')
"
    fi
  fi
}

_zip_dir_recursive() {
  local src="$1"
  local out="$2"
  if command -v zip >/dev/null 2>&1; then
    ( cd "$src" && zip -rq "$out" . )
    return
  fi
  "$PYTHON" - "$src" "$out" <<'PY'
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(src):
        for name in files:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                zf.write(path, os.path.relpath(path, src))
PY
}

_build_catalog_zip() {
  local zip_path="$1"
  local build_dir="$2"
  rm -rf "$build_dir"
  mkdir -p "$build_dir"
  ( cd "$LAMBDA_DIR" && \
    find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
      | xargs -0 -I{} cp --parents '{}' "$build_dir" )
  local req="$LAMBDA_DIR/requirements.txt"
  if [[ -f "$req" ]]; then
    pip install \
      --quiet \
      --platform manylinux2014_x86_64 \
      --only-binary=:all: \
      --python-version 3.11 \
      --implementation cp \
      -r "$req" \
      -t "$build_dir/_vendor"
  fi
  _zip_dir_recursive "$build_dir" "$zip_path"
}

_build_token_authorizer_zip() {
  local zip_path="$1"
  local build_dir="$2"
  rm -rf "$build_dir"
  mkdir -p "$build_dir"
  ( cd "$AUTH_LAMBDA_DIR" && \
    find . -type f ! -path './_vendor/*' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 \
      | xargs -0 -I{} cp --parents '{}' "$build_dir" )
  local req="$AUTH_LAMBDA_DIR/requirements.txt"
  if [[ -f "$req" ]]; then
    pip install \
      --quiet \
      --platform manylinux2014_x86_64 \
      --only-binary=:all: \
      --python-version 3.11 \
      --implementation cp \
      -r "$req" \
      -t "$build_dir/_vendor"
  fi
  _zip_dir_recursive "$build_dir" "$zip_path"
}

_upload_catalog_bundles() {
  if ! aws s3api head-bucket --bucket "$ARTIFACT_BUCKET" --region "$REGION" 2>/dev/null; then
    echo "Creating artifacts bucket: $ARTIFACT_BUCKET"
    aws s3 mb "s3://${ARTIFACT_BUCKET}" --region "$REGION"
    aws s3api put-bucket-versioning \
      --bucket "$ARTIFACT_BUCKET" \
      --versioning-configuration Status=Enabled \
      --region "$REGION"
  fi
  local zip="/tmp/catalog-lambda-dev-$$.zip"
  local build="/tmp/catalog-build-dev-$$"
  local auth_zip="/tmp/catalog-token-authorizer-dev-$$.zip"
  local auth_build="/tmp/catalog-token-authorizer-build-dev-$$"
  trap 'rm -f "$zip" "$auth_zip"; rm -rf "$build" "$auth_build"' RETURN
  _build_catalog_zip "$zip" "$build"
  _build_token_authorizer_zip "$auth_zip" "$auth_build"
  aws s3 cp "$zip" "s3://${ARTIFACT_BUCKET}/${ZIP_KEY}" --region "$REGION"
  aws s3 cp "$auth_zip" "s3://${ARTIFACT_BUCKET}/${AUTH_ZIP_KEY}" --region "$REGION"
}

_package_cognito_profile_sync() {
  local key="cognito-user-profile-sync-dev-${SUFFIX}.zip"
  local stage
  stage="$(mktemp -d)"
  local pkg="$stage/pkg"
  mkdir -p "$pkg"
  cp "$ROOT/infrastructure/lambda/cognito_user_profile_sync/_vendor_bootstrap.py" "$pkg/"
  cp "$ROOT/infrastructure/lambda/cognito_user_profile_sync/handler.py" "$pkg/"
  cp "$ROOT/infrastructure/lambda/cognito_user_profile_sync/session_sync.py" "$pkg/"
  cp "$ROOT/infrastructure/lambda/cognito_user_profile_sync/sync_config.py" "$pkg/"
  cp "$ROOT/infrastructure/lambda/cognito_user_profile_sync/repo.py" "$pkg/"
  cp "$ROOT/infrastructure/lambda/catalog/dsql_connect.py" "$pkg/"
  cp "$ROOT/infrastructure/lambda/catalog/services/common/db_tx.py" "$pkg/db_tx.py"
  pip install -r "$ROOT/infrastructure/lambda/cognito_user_profile_sync/requirements.txt" \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    -t "$pkg/_vendor"
  (cd "$pkg" && zip -rq "$stage/bundle.zip" .)
  aws s3 cp "$stage/bundle.zip" "s3://${ARTIFACT_BUCKET}/${key}" --region "$REGION"
  echo "${ARTIFACT_BUCKET} ${key}"
}

_package_cognito_pre_signup() {
  local key="cognito-pre-signup-dev-${SUFFIX}.zip"
  local stage
  stage="$(mktemp -d)"
  local pkg="$stage/pkg"
  mkdir -p "$pkg"
  cp "$ROOT/infrastructure/lambda/cognito_pre_signup/handler.py" "$pkg/"
  cp "$ROOT/infrastructure/lambda/cognito_pre_signup/linking.py" "$pkg/"
  (cd "$pkg" && zip -rq "$stage/bundle.zip" .)
  aws s3 cp "$stage/bundle.zip" "s3://${ARTIFACT_BUCKET}/${key}" --region "$REGION"
  echo "${ARTIFACT_BUCKET} ${key}"
}

_auth_overrides_to_args() {
  local sync_bucket="$1"
  local sync_key="$2"
  local pre_bucket="$3"
  local pre_key="$4"
  local student_id="${5:-}"
  local teacher_id="${6:-}"
  local domain_prefix="${DEV_COGNITO_DOMAIN_PREFIX:-}"
  mapfile -t OVERRIDES < <("$PYTHON" - <<PY
import sys
sys.path.insert(0, "${ROOT}/scripts")
from dev_stage import auth_parameter_overrides
import os
overrides = auth_parameter_overrides(
    google_client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
    google_client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
    dsql_endpoint="${DSQL_ENDPOINT}",
    dsql_cluster_arn="${DSQL_CLUSTER_ARN}",
    profile_sync_bucket="${sync_bucket}",
    profile_sync_key="${sync_key}",
    pre_signup_bucket="${pre_bucket}",
    pre_signup_key="${pre_key}",
    cognito_domain_prefix="${domain_prefix}" or None,
    student_cognito_client_id="${student_id}",
    teacher_cognito_client_id="${teacher_id}",
)
for o in overrides:
    print(o)
PY
)
  AUTH_OVERRIDE_ARGS=()
  for item in "${OVERRIDES[@]}"; do
    AUTH_OVERRIDE_ARGS+=("$item")
  done
}

_api_overrides_to_args() {
  local video_bucket="$1"
  local pool_arn="$2"
  local client_ids="$3"
  local student_id="$4"
  mapfile -t OVERRIDES < <("$PYTHON" - <<PY
import sys
sys.path.insert(0, "${ROOT}/scripts")
from dev_stage import api_parameter_overrides
overrides = api_parameter_overrides(
    video_bucket_name="${video_bucket}",
    dsql_endpoint="${DSQL_ENDPOINT}",
    dsql_cluster_arn="${DSQL_CLUSTER_ARN}",
    cognito_user_pool_arn="${pool_arn}",
    cognito_client_id="${client_ids}",
    student_cognito_client_id="${student_id}",
    lambda_code_bucket="${ARTIFACT_BUCKET}",
    lambda_code_key="${ZIP_KEY}",
    token_authorizer_key="${AUTH_ZIP_KEY}",
)
for o in overrides:
    print(o)
PY
)
  API_OVERRIDE_ARGS=()
  for item in "${OVERRIDES[@]}"; do
    API_OVERRIDE_ARGS+=("$item")
  done
}

case "$SUB" in
dsql)
  aws cloudformation validate-template \
    --template-body "file://${TEMPLATE_DIR}/dsql-stack.yaml" \
    --region "$REGION"
  aws cloudformation deploy \
    --template-file "${TEMPLATE_DIR}/dsql-stack.yaml" \
    --stack-name "$DSQL_STACK" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
  --parameter-overrides "Environment=dev"
  ;;

schema)
  _dsql_dev_outputs
  _assert_dsql_differs_from_prod
  export PYTHONPATH="${ROOT}/infrastructure/lambda/catalog:${PYTHONPATH:-}"
  "$PYTHON" "${ROOT}/scripts/apply-dsql-schema.py" \
    --host "$DSQL_ENDPOINT" \
    --iam-role-arn "arn:aws:iam::${ACCOUNT}:role/StreamMyCourse-CatalogLambdaRole-dev" \
    --iam-role-arn "arn:aws:iam::${ACCOUNT}:role/StreamMyCourse-Auth-dev-UserProfileSyncLambdaRole"
  ;;

auth)
  if [[ -z "${GOOGLE_OAUTH_CLIENT_ID:-}" || -z "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]]; then
    echo "Set GitHub Environment dev secrets GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET" >&2
    exit 1
  fi
  _dsql_dev_outputs
  _assert_dsql_differs_from_prod
  read -r SYNC_BUCKET SYNC_KEY < <(_package_cognito_profile_sync)
  read -r PRE_BUCKET PRE_KEY < <(_package_cognito_pre_signup)
  _auth_overrides_to_args "$SYNC_BUCKET" "$SYNC_KEY" "$PRE_BUCKET" "$PRE_KEY"
  aws cloudformation validate-template \
    --template-body "file://${TEMPLATE_DIR}/auth-stack.yaml" \
    --region "$REGION"
  aws cloudformation deploy \
    --template-file "${TEMPLATE_DIR}/auth-stack.yaml" \
    --stack-name "$AUTH_STACK" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --parameter-overrides "${AUTH_OVERRIDE_ARGS[@]}"
  student_client_id="$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='StudentUserPoolClientId'].OutputValue" \
    --output text 2>/dev/null || true)"
  teacher_client_id="$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='TeacherUserPoolClientId'].OutputValue" \
    --output text 2>/dev/null || true)"
  if [[ -n "$student_client_id" && "$student_client_id" != "None" && -n "$teacher_client_id" && "$teacher_client_id" != "None" ]]; then
    _auth_overrides_to_args "$SYNC_BUCKET" "$SYNC_KEY" "$PRE_BUCKET" "$PRE_KEY" "$student_client_id" "$teacher_client_id"
    aws cloudformation deploy \
      --template-file "${TEMPLATE_DIR}/auth-stack.yaml" \
      --stack-name "$AUTH_STACK" \
      --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
      --region "$REGION" \
      --no-fail-on-empty-changeset \
      --parameter-overrides "${AUTH_OVERRIDE_ARGS[@]}"
  fi
  ;;

video)
  aws cloudformation validate-template \
    --template-body "file://${TEMPLATE_DIR}/dev-video-bucket-stack.yaml" \
    --region "$REGION"
  aws cloudformation deploy \
    --template-file "${TEMPLATE_DIR}/dev-video-bucket-stack.yaml" \
    --stack-name "$VIDEO_STACK" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --parameter-overrides "Environment=dev"
  ;;

api)
  _dsql_dev_outputs
  _assert_dsql_differs_from_prod
  VIDEO_BUCKET="$(aws cloudformation describe-stacks \
    --stack-name "$VIDEO_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
    --output text)"
  if [[ -z "$VIDEO_BUCKET" || "$VIDEO_BUCKET" == "None" ]]; then
    echo "Missing BucketName on $VIDEO_STACK" >&2
    exit 1
  fi
  if ! aws cloudformation describe-stacks --stack-name "$AUTH_STACK" --region "$REGION" &>/dev/null; then
    echo "Auth stack $AUTH_STACK must exist before API deploy" >&2
    exit 1
  fi
  POOL_ARN="$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolArn'].OutputValue" \
    --output text)"
  STUDENT_CLIENT="$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='StudentUserPoolClientId'].OutputValue" \
    --output text)"
  TEACHER_CLIENT="$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='TeacherUserPoolClientId'].OutputValue" \
    --output text)"
  CID_PARTS=()
  if [[ -n "$TEACHER_CLIENT" && "$TEACHER_CLIENT" != "None" ]]; then
    CID_PARTS+=("$TEACHER_CLIENT")
  fi
  if [[ -n "$STUDENT_CLIENT" && "$STUDENT_CLIENT" != "None" && "$STUDENT_CLIENT" != "$TEACHER_CLIENT" ]]; then
    CID_PARTS+=("$STUDENT_CLIENT")
  fi
  COGNITO_CLIENT_IDS="$(IFS=,; echo "${CID_PARTS[*]}")"
  _upload_catalog_bundles
  _api_overrides_to_args "$VIDEO_BUCKET" "$POOL_ARN" "$COGNITO_CLIENT_IDS" "$STUDENT_CLIENT"
  aws cloudformation deploy \
    --template-file "${TEMPLATE_DIR}/api-stack.yaml" \
    --s3-bucket "$ARTIFACT_BUCKET" \
    --s3-prefix "cf-api-template/dev/" \
    --stack-name "$API_STACK" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --parameter-overrides "${API_OVERRIDE_ARGS[@]}"
  ;;

*)
  echo "Unknown subcommand: $SUB" >&2
  exit 1
  ;;
esac