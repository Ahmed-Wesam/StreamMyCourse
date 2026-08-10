#!/usr/bin/env bash
# Restore prod from pause manifest (retained S3 buckets + RDS snapshot).
#
# Usage:
#   ./scripts/restore-prod.sh --manifest PATH [--confirm] [--dry-run]
#
# Mutating operations require --confirm. Use --dry-run to preview steps without AWS changes.
# Required env for edge import/deploy: ROUTE53_HOSTED_ZONE_ID, STUDENT_WEB_DOMAIN, TEACHER_WEB_DOMAIN
# Required env for auth deploy: COGNITO_DOMAIN_PREFIX, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES="$ROOT/infrastructure/templates"
# shellcheck source=scripts/lib/prod_pause_constants.sh
source "$SCRIPT_DIR/lib/prod_pause_constants.sh"

ENV="prod"
REGION_EU="eu-west-1"
REGION_US="us-east-1"
EDGE_STACK="StreamMyCourse-EdgeHosting-${ENV}"
VIDEO_STACK="StreamMyCourse-Video-${ENV}"
RDS_STACK="StreamMyCourse-Rds-${ENV}"
AUTH_STACK="StreamMyCourse-Auth-${ENV}"

MANIFEST=""
DRY_RUN=false
CONFIRM=false

usage() {
  echo "Usage: $0 --manifest PATH [--confirm] [--dry-run]" >&2
  echo "  --manifest PATH   Pause manifest JSON from export-pause-manifest.sh (required)." >&2
  echo "  --confirm         Required for mutating operations; prompts for AWS account ID." >&2
  echo "  --dry-run         Print restore steps without mutating AWS resources." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
  --manifest)
    shift
    MANIFEST="${1:?--manifest requires a path}"
    ;;
  --confirm)
    CONFIRM=true
    ;;
  --dry-run)
    DRY_RUN=true
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown argument: $1" >&2
    usage
    exit 1
    ;;
  esac
  shift
done

if [[ -z "$MANIFEST" ]]; then
  echo "--manifest is required." >&2
  usage
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "Manifest not found: $MANIFEST" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for manifest parsing." >&2
  exit 1
fi

refuse_without_confirm() {
  echo "Refusing mutating operation without --confirm (use --dry-run to preview)." >&2
  exit 1
}

if [[ "$DRY_RUN" != true && "$CONFIRM" != true ]]; then
  refuse_without_confirm
fi

validate_manifest() {
  local key val
  for key in aws_account_id video_bucket_name student_bucket_name teacher_bucket_name rds_snapshot_identifier regions; do
    val="$(jq -r ".${key} // empty" "$MANIFEST" | tr -d '\r')"
    if [[ -z "$val" || "$val" == "null" ]]; then
      echo "Manifest missing required key: ${key}" >&2
      exit 1
    fi
  done
  if [[ "$(jq -r '.regions | length' "$MANIFEST")" -lt 1 ]]; then
    echo "Manifest regions must be a non-empty array." >&2
    exit 1
  fi
  if [[ -z "$(jq -r '.rds_snapshot_identifier' "$MANIFEST" | tr -d '\r')" ]]; then
    echo "Manifest rds_snapshot_identifier must be non-empty." >&2
    exit 1
  fi
}

manifest_get() {
  jq -r ".$1" "$MANIFEST" | tr -d '\r'
}

stack_exists() {
  local stack="$1"
  local region="$2"
  aws cloudformation describe-stacks --stack-name "$stack" --region "$region" >/dev/null 2>&1
}

bucket_exists() {
  local bucket="$1"
  local region="$2"
  aws s3api head-bucket --bucket "$bucket" --region "$region" >/dev/null 2>&1
}

template_uri() {
  local path="$1"
  if command -v cygpath >/dev/null 2>&1; then
    echo "file://$(cygpath -m "$path")"
  else
    echo "file://${path}"
  fi
}

require_edge_env() {
  : "${ROUTE53_HOSTED_ZONE_ID:?ROUTE53_HOSTED_ZONE_ID is required for edge stack import/deploy}"
  : "${STUDENT_WEB_DOMAIN:?STUDENT_WEB_DOMAIN is required for edge stack import/deploy}"
  : "${TEACHER_WEB_DOMAIN:?TEACHER_WEB_DOMAIN is required for edge stack import/deploy}"
}

edge_parameter_overrides() {
  local cert_primary="${WEB_CERT_DOMAIN:-$STUDENT_WEB_DOMAIN}"
  local attach="${EDGE_ATTACH_CF_ALIASES:-true}"
  EDGE_OVERRIDES=(
    "Environment=${ENV}"
    "HostedZoneId=${ROUTE53_HOSTED_ZONE_ID}"
    "CertPrimaryDomain=${cert_primary}"
    "StudentDomainName=${STUDENT_WEB_DOMAIN}"
    "TeacherDomainName=${TEACHER_WEB_DOMAIN}"
    "PriceClass=PriceClass_100"
    "AttachCloudFrontAliases=${attach}"
  )
  if [[ -n "${WEB_CERT_SANS:-}" ]]; then
    EDGE_OVERRIDES+=("SubjectAlternativeNames=${WEB_CERT_SANS}")
  fi
}

cfn_parameters_from_overrides() {
  local out=()
  local pair key val
  for pair in "$@"; do
    key="${pair%%=*}"
    val="${pair#*=}"
    out+=("ParameterKey=${key},ParameterValue=${val}")
  done
  printf '%s\n' "${out[@]}"
}

import_retained_bucket_stack() {
  local stack="$1"
  local region="$2"
  local template="$3"
  local import_file="$4"
  shift 4
  local overrides=("$@")

  if stack_exists "$stack" "$region"; then
    echo "Stack ${stack} already exists in ${region}; skipping import."
    return 0
  fi

  local bucket_name
  for bucket_name in $(jq -r '.[].ResourceIdentifier.BucketName' "$import_file" | tr -d '\r'); do
    if [[ -z "$bucket_name" || "$bucket_name" == "null" ]]; then
      continue
    fi
    if ! bucket_exists "$bucket_name" "$region"; then
      echo "Retained bucket not found: ${bucket_name} (region ${region}). Cannot import ${stack}." >&2
      exit 1
    fi
    echo "Found retained bucket: ${bucket_name}"
  done

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would import stack ${stack} (${region}) from ${template}"
    echo "[dry-run] Resources to import:"
    jq -c '.[]' "$import_file"
    return 0
  fi

  local params
  mapfile -t params < <(cfn_parameters_from_overrides "${overrides[@]}")
  echo "Importing stack ${stack} (${region})..."

  local import_path="${ROOT}/.restore-import-${stack}.json"
  cp "$import_file" "$import_path"
  local import_uri
  if command -v cygpath >/dev/null 2>&1; then
    import_uri="file://$(cygpath -m "$import_path")"
  else
    import_uri="file://${import_path}"
  fi

  local cs_name="restore-import-$(date +%s)"
  aws cloudformation create-change-set \
    --stack-name "$stack" \
    --change-set-name "$cs_name" \
    --change-set-type IMPORT \
    --region "$region" \
    --template-body "$(template_uri "$template")" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameters "${params[@]}" \
    --resources-to-import "$import_uri"
  aws cloudformation wait change-set-create-complete \
    --stack-name "$stack" \
    --change-set-name "$cs_name" \
    --region "$region"
  aws cloudformation execute-change-set \
    --stack-name "$stack" \
    --change-set-name "$cs_name" \
    --region "$region"
  aws cloudformation wait stack-import-complete --stack-name "$stack" --region "$region" 2>/dev/null \
    || aws cloudformation wait stack-create-complete --stack-name "$stack" --region "$region"
  rm -f "$import_path"
  echo "Imported ${stack}"
}

import_edge_stack() {
  require_edge_env
  edge_parameter_overrides

  local import_file
  import_file="$(mktemp)"
  local student_bucket teacher_bucket
  student_bucket="$(manifest_get student_bucket_name)"
  teacher_bucket="$(manifest_get teacher_bucket_name)"
  jq -n \
    --arg site "$student_bucket" \
    --arg teacher "$teacher_bucket" \
    '[
      {"ResourceType":"AWS::S3::Bucket","LogicalResourceId":"SiteBucket","ResourceIdentifier":{"BucketName":$site}},
      {"ResourceType":"AWS::S3::Bucket","LogicalResourceId":"TeacherSiteBucket","ResourceIdentifier":{"BucketName":$teacher}}
    ]' >"$import_file"

  import_retained_bucket_stack \
    "$EDGE_STACK" \
    "$REGION_US" \
    "$TEMPLATES/edge-hosting-stack.yaml" \
    "$import_file" \
    "${EDGE_OVERRIDES[@]}"
  rm -f "$import_file"
}

package_invalidation_lambda() {
  local account bucket key suffix stage inv_dir inv_zip
  account="$(aws sts get-caller-identity --query Account --output text --region "$REGION_EU")"
  bucket="streammycourse-artifacts-${account}-${REGION_EU}"
  if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
    suffix="$(git -C "$ROOT" rev-parse HEAD | cut -c1-12)"
  else
    suffix="$(date +%s)"
  fi
  key="cf-invalidate-restore-${suffix}.zip"
  stage="$(mktemp -d)"
  inv_dir="${ROOT}/infrastructure/lambda/cloudfront_invalidation"
  inv_zip="${stage}/bundle.zip"
  if [[ ! -f "${inv_dir}/index.py" ]]; then
    echo "Missing CloudFront invalidation Lambda: ${inv_dir}/index.py" >&2
    exit 1
  fi
  if command -v zip >/dev/null 2>&1; then
    (cd "$inv_dir" && zip -q "$inv_zip" index.py)
  else
    python3 - "$inv_dir" "$inv_zip" <<'PY'
import sys, zipfile
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(src / "index.py", "index.py")
PY
  fi
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would upload invalidation Lambda to s3://${bucket}/${key}"
    rm -rf "$stage"
    INVALIDATION_BUCKET="$bucket"
    INVALIDATION_KEY="$key"
    return 0
  fi
  if ! aws s3api head-bucket --bucket "$bucket" --region "$REGION_EU" 2>/dev/null; then
    aws s3 mb "s3://${bucket}" --region "$REGION_EU"
  fi
  aws s3 cp "$inv_zip" "s3://${bucket}/${key}" --region "$REGION_EU"
  rm -rf "$stage"
  INVALIDATION_BUCKET="$bucket"
  INVALIDATION_KEY="$key"
}

import_video_stack() {
  local video_bucket cors import_file overrides
  video_bucket="$(manifest_get video_bucket_name)"
  cors="https://researchspectrum.org,https://teach.researchspectrum.org,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"

  package_invalidation_lambda

  import_file="$(mktemp)"
  jq -n --arg bucket "$video_bucket" \
    '[{"ResourceType":"AWS::S3::Bucket","LogicalResourceId":"VideoBucket","ResourceIdentifier":{"BucketName":$bucket}}]' \
    >"$import_file"

  overrides=(
    "Environment=${ENV}"
    "InvalidationLambdaCodeS3Bucket=${INVALIDATION_BUCKET}"
    "InvalidationLambdaCodeS3Key=${INVALIDATION_KEY}"
    "CorsAllowedOrigins=${cors}"
  )

  import_retained_bucket_stack \
    "$VIDEO_STACK" \
    "$REGION_EU" \
    "$TEMPLATES/video-stack.yaml" \
    "$import_file" \
    "${overrides[@]}"
  rm -f "$import_file"
}

deploy_edge() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would run: $SCRIPT_DIR/deploy-edge.sh ${ENV}"
    return 0
  fi
  require_edge_env
  "$SCRIPT_DIR/deploy-edge.sh" "$ENV"
}

deploy_rds_from_snapshot() {
  local snapshot
  snapshot="$(manifest_get rds_snapshot_identifier)"
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would run: RESTORE_DB_SNAPSHOT_IDENTIFIER=${snapshot} $SCRIPT_DIR/deploy-rds-stack.sh ${ENV}"
    return 0
  fi
  RESTORE_DB_SNAPSHOT_IDENTIFIER="$snapshot" "$SCRIPT_DIR/deploy-rds-stack.sh" "$ENV"
}

sync_rds_secret() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would run: $SCRIPT_DIR/sync-rds-secret-after-restore.sh ${ENV}"
    return 0
  fi
  "$SCRIPT_DIR/sync-rds-secret-after-restore.sh" "$ENV"
}

invoke_schema_applier() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would invoke schema-applier Lambda from ${RDS_STACK} output SchemaApplierFunctionName"
    return 0
  fi
  local fn out
  fn="$(aws cloudformation describe-stacks \
    --stack-name "$RDS_STACK" \
    --region "$REGION_EU" \
    --query "Stacks[0].Outputs[?OutputKey=='SchemaApplierFunctionName'].OutputValue" \
    --output text)"
  if [[ -z "$fn" || "$fn" == "None" ]]; then
    echo "Missing CloudFormation output SchemaApplierFunctionName. Deploy RDS with SchemaApplierCodeS3Bucket/Key." >&2
    exit 1
  fi
  out="$(mktemp)"
  aws lambda invoke \
    --region "$REGION_EU" \
    --function-name "$fn" \
    --cli-binary-format raw-in-base64-out \
    --payload '{}' \
    "$out"
  if jq -e 'has("errorMessage")' "$out" >/dev/null 2>&1; then
    echo "Schema applier Lambda raised (FunctionError)" >&2
    jq -c '{errorMessage, errorType}' "$out" >&2
    rm -f "$out"
    exit 1
  fi
  if ! jq -e '.ok == true' "$out" >/dev/null 2>&1; then
    echo "Schema applier returned non-success payload:" >&2
    jq -c '{ok, error}' "$out" >&2 || cat "$out" >&2
    rm -f "$out"
    exit 1
  fi
  rm -f "$out"
  echo "Schema applier succeeded."
}

package_cognito_sync_lambda() {
  local account bucket key suffix stage pkg ws
  : "${COGNITO_DOMAIN_PREFIX:?COGNITO_DOMAIN_PREFIX is required for auth stack deploy}"
  : "${GOOGLE_OAUTH_CLIENT_ID:?GOOGLE_OAUTH_CLIENT_ID is required for auth stack deploy}"
  : "${GOOGLE_OAUTH_CLIENT_SECRET:?GOOGLE_OAUTH_CLIENT_SECRET is required for auth stack deploy}"

  account="$(aws sts get-caller-identity --query Account --output text --region "$REGION_EU")"
  bucket="streammycourse-artifacts-${account}-${REGION_EU}"
  if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
    suffix="$(git -C "$ROOT" rev-parse HEAD | cut -c1-12)"
  else
    suffix="$(date +%s)"
  fi
  key="cognito-user-profile-sync-restore-${suffix}.zip"

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would package and upload Cognito user profile sync Lambda to s3://${bucket}/${key}"
    COGNITO_SYNC_BUCKET="$bucket"
    COGNITO_SYNC_KEY="$key"
    return 0
  fi

  stage="$(mktemp -d)"
  pkg="${stage}/pkg"
  mkdir -p "$pkg"
  ws="${ROOT}/infrastructure/lambda/cognito_user_profile_sync"
  cp "$ws/_vendor_bootstrap.py" "$ws/handler.py" "$ws/session_sync.py" "$ws/sync_config.py" "$ws/repo.py" "$pkg/"
  pip install psycopg2-binary==2.9.9 \
    --quiet \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --implementation cp \
    -t "$pkg/_vendor"
  (cd "$pkg" && zip -rq "${stage}/bundle.zip" .)
  if ! aws s3api head-bucket --bucket "$bucket" --region "$REGION_EU" 2>/dev/null; then
    aws s3 mb "s3://${bucket}" --region "$REGION_EU"
  fi
  aws s3 cp "${stage}/bundle.zip" "s3://${bucket}/${key}" --region "$REGION_EU"
  rm -rf "$stage"
  COGNITO_SYNC_BUCKET="$bucket"
  COGNITO_SYNC_KEY="$key"
  echo "Uploaded Cognito profile sync s3://${bucket}/${key}"
}

deploy_auth_stack() {
  package_cognito_sync_lambda

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would deploy auth stack: $TEMPLATES/auth-stack.yaml ($AUTH_STACK)"
    return 0
  fi

  aws cloudformation validate-template \
    --template-body "$(template_uri "$TEMPLATES/auth-stack.yaml")" \
    --region "$REGION_EU"

  local auth_overrides=(
    "Environment=${ENV}"
    "CognitoDomainPrefix=${COGNITO_DOMAIN_PREFIX}"
    "GoogleClientId=${GOOGLE_OAUTH_CLIENT_ID}"
    "GoogleClientSecret=${GOOGLE_OAUTH_CLIENT_SECRET}"
    "RdsStackName=${RDS_STACK}"
    "EnableUserProfileSync=true"
    "CognitoUserProfileSyncCodeS3Bucket=${COGNITO_SYNC_BUCKET}"
    "CognitoUserProfileSyncCodeS3Key=${COGNITO_SYNC_KEY}"
  )
  if [[ -n "${STUDENT_COGNITO_CALLBACK_URLS:-}" ]]; then
    auth_overrides+=("StudentCallbackUrls=${STUDENT_COGNITO_CALLBACK_URLS}")
  fi
  if [[ -n "${STUDENT_COGNITO_LOGOUT_URLS:-}" ]]; then
    auth_overrides+=("StudentLogoutUrls=${STUDENT_COGNITO_LOGOUT_URLS}")
  fi
  if [[ -n "${TEACHER_COGNITO_CALLBACK_URLS:-}" ]]; then
    auth_overrides+=("TeacherCallbackUrls=${TEACHER_COGNITO_CALLBACK_URLS}")
  fi
  if [[ -n "${TEACHER_COGNITO_LOGOUT_URLS:-}" ]]; then
    auth_overrides+=("TeacherLogoutUrls=${TEACHER_COGNITO_LOGOUT_URLS}")
  fi

  aws cloudformation deploy \
    --template-file "$TEMPLATES/auth-stack.yaml" \
    --stack-name "$AUTH_STACK" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region "$REGION_EU" \
    --no-fail-on-empty-changeset \
    --parameter-overrides "${auth_overrides[@]}"

  local student_client_id teacher_client_id
  student_client_id="$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --region "$REGION_EU" \
    --query "Stacks[0].Outputs[?OutputKey=='StudentUserPoolClientId'].OutputValue" \
    --output text 2>/dev/null || true)"
  teacher_client_id="$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --region "$REGION_EU" \
    --query "Stacks[0].Outputs[?OutputKey=='TeacherUserPoolClientId'].OutputValue" \
    --output text 2>/dev/null || true)"

  if [[ -n "$student_client_id" && "$student_client_id" != "None" && -n "$teacher_client_id" && "$teacher_client_id" != "None" ]]; then
    auth_overrides+=(
      "StudentCognitoClientId=${student_client_id}"
      "TeacherCognitoClientId=${teacher_client_id}"
    )
    aws cloudformation deploy \
      --template-file "$TEMPLATES/auth-stack.yaml" \
      --stack-name "$AUTH_STACK" \
      --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
      --region "$REGION_EU" \
      --no-fail-on-empty-changeset \
      --parameter-overrides "${auth_overrides[@]}"
  fi
  echo "Auth stack deployed: ${AUTH_STACK}"
}

deploy_backend() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would run: VIDEO_PROVIDER=s3 $SCRIPT_DIR/deploy-backend.sh ${ENV}"
    return 0
  fi
  VIDEO_PROVIDER="${VIDEO_PROVIDER:-s3}" "$SCRIPT_DIR/deploy-backend.sh" "$ENV"
}

print_next_steps() {
  echo ""
  echo "=== Next steps ==="
  echo "1. Sync GitHub Environment secrets from auth stack outputs:"
  echo "     .\\scripts\\set-github-auth-secrets-from-stack.ps1 -Environment prod"
  echo "2. Run integration tests against prod:"
  echo "     .\\scripts\\run-integration-tests.ps1"
  echo "     # or: ./scripts/run-local-integration-tests.sh"
  echo "3. Deploy student + teacher SPAs via GitHub Actions (push main or workflow_dispatch deploy workflows)."
  echo ""
}

validate_manifest

MANIFEST_ACCOUNT="$(manifest_get aws_account_id)"
CURRENT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
echo "Manifest account: ${MANIFEST_ACCOUNT}"
echo "Current AWS account: ${CURRENT_ACCOUNT}"

if [[ "$CURRENT_ACCOUNT" != "$MANIFEST_ACCOUNT" ]]; then
  echo "Current AWS account does not match manifest aws_account_id. Aborting." >&2
  exit 1
fi

if [[ "$CONFIRM" == true && "$DRY_RUN" != true ]]; then
  echo -n "Type AWS account ID (${MANIFEST_ACCOUNT}) to confirm prod restore: "
  read -r typed_account
  if [[ "$typed_account" != "$MANIFEST_ACCOUNT" ]]; then
    echo "Account ID mismatch. Aborting." >&2
    exit 1
  fi
fi

echo ""
echo "=== Prod restore (manifest: ${MANIFEST}) ==="
if [[ "$DRY_RUN" == true ]]; then
  echo "Mode: dry-run (no AWS mutations)"
else
  echo "Mode: confirm (mutating)"
fi

echo ""
echo "--- Step 1: Import retained S3 buckets (edge + video) ---"
if [[ "${RESTORE_SKIP_IMPORT:-}" == "1" ]]; then
  echo "RESTORE_SKIP_IMPORT=1: skipping CFN bucket import (edge/video stacks will be created fresh)."
else
  import_edge_stack
  import_video_stack
fi

echo ""
echo "--- Step 2: Deploy edge hosting ---"
deploy_edge

echo ""
echo "--- Step 3: Deploy RDS from snapshot ---"
deploy_rds_from_snapshot

echo ""
echo "--- Step 4: Sync RDS secret after restore ---"
sync_rds_secret

echo ""
echo "--- Step 5: Apply PostgreSQL schema (schema-applier Lambda) ---"
invoke_schema_applier

if [[ "${RESTORE_STOP_AFTER:-}" == "schema" ]]; then
  echo ""
  echo "RESTORE_STOP_AFTER=schema: stopping before auth/backend (run GitHub Deploy workflow to finish)."
  print_next_steps
  exit 0
fi

echo ""
echo "--- Step 6: Deploy auth stack (Cognito) ---"
deploy_auth_stack

echo ""
echo "--- Step 7: Deploy backend (video + API) ---"
deploy_backend

echo ""
if [[ "$DRY_RUN" == true ]]; then
  echo "Dry-run complete (account ${CURRENT_ACCOUNT}). No resources were changed."
else
  echo "Prod restore complete (account ${CURRENT_ACCOUNT})."
fi

print_next_steps
