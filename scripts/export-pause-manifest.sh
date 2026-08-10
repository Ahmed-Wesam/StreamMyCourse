#!/usr/bin/env bash
# Export prod pause/restore manifest from live CloudFormation stack outputs (no secret values).
# Usage: ./scripts/export-pause-manifest.sh [--out PATH]
# Default output: pause-manifest.json (gitignored — store off-repo after export).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=scripts/lib/prod_pause_constants.sh
source "$SCRIPT_DIR/lib/prod_pause_constants.sh"

OUT_PATH="pause-manifest.json"

usage() {
  echo "Usage: $0 [--out PATH]" >&2
  echo "  Writes pause manifest JSON (default: pause-manifest.json)." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
  --out)
    shift
    OUT_PATH="${1:?--out requires a path}"
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

REGION_EU="eu-west-1"
REGION_US="us-east-1"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

STACK_VIDEO="StreamMyCourse-Video-prod"
STACK_EDGE="StreamMyCourse-EdgeHosting-prod"
STACK_API="StreamMyCourse-Api-prod"
STACK_AUTH="StreamMyCourse-Auth-prod"
STACK_RDS="StreamMyCourse-Rds-prod"

cfn_output() {
  local stack="$1" region="$2" key="$3"
  if ! aws cloudformation describe-stacks --stack-name "$stack" --region "$region" &>/dev/null; then
    echo ""
    return 0
  fi
  local val
  val="$(aws cloudformation describe-stacks \
    --stack-name "$stack" \
    --region "$region" \
    --query "Stacks[0].Outputs[?OutputKey=='${key}'].OutputValue | [0]" \
    --output text 2>/dev/null || true)"
  if [[ -z "$val" || "$val" == "None" ]]; then
    echo ""
  else
    echo "$val"
  fi
}

aws_account_id="$(aws sts get-caller-identity --query Account --output text)"

video_bucket_name="$(cfn_output "$STACK_VIDEO" "$REGION_EU" BucketName)"
student_bucket_name="$(cfn_output "$STACK_EDGE" "$REGION_US" StudentBucketName)"
teacher_bucket_name="$(cfn_output "$STACK_EDGE" "$REGION_US" TeacherBucketName)"
api_endpoint="$(cfn_output "$STACK_API" "$REGION_EU" ApiEndpoint)"
user_pool_id="$(cfn_output "$STACK_AUTH" "$REGION_EU" UserPoolId)"
student_user_pool_client_id="$(cfn_output "$STACK_AUTH" "$REGION_EU" StudentUserPoolClientId)"
teacher_user_pool_client_id="$(cfn_output "$STACK_AUTH" "$REGION_EU" TeacherUserPoolClientId)"
cognito_hosted_ui_domain="$(cfn_output "$STACK_AUTH" "$REGION_EU" HostedUIDomain)"
rds_db_host="$(cfn_output "$STACK_RDS" "$REGION_EU" DbHost)"

# rds_snapshot_identifier: fill after manual pause snapshot (see runbook) OR record the
# auto-created final snapshot ID after StreamMyCourse-Rds-prod stack delete / teardown.
rds_snapshot_identifier=""

# GitHub Environment prod checklist — names only (no values); from prod-shutdown-restore plan.
GITHUB_ENV_CHECKLIST=(
  "AWS_DEPLOY_ROLE_ARN"
  "COGNITO_DOMAIN_PREFIX"
  "ROUTE53_HOSTED_ZONE_ID"
  "STUDENT_WEB_DOMAIN"
  "TEACHER_WEB_DOMAIN"
  "GOOGLE_OAUTH_CLIENT_ID"
  "GOOGLE_OAUTH_CLIENT_SECRET"
  "COGNITO_RDS_VERIFY_TEST_PASSWORD"
  "COGNITO_RDS_VERIFY_JWT"
  "COGNITO_RDS_VERIFY_TEST_USERNAME"
  "COGNITO_RDS_VERIFY_TEST_PASSWORD_ALT"
  "COGNITO_RDS_VERIFY_TEST_USERNAME_ALT"
  "COGNITO_RDS_VERIFY_TEST_PASSWORD_STUDENT"
  "COGNITO_RDS_VERIFY_TEST_USERNAME_STUDENT"
)

export OUT_PATH \
  aws_account_id \
  video_bucket_name student_bucket_name teacher_bucket_name \
  api_endpoint user_pool_id student_user_pool_client_id teacher_user_pool_client_id \
  cognito_hosted_ui_domain rds_db_host rds_snapshot_identifier

PAUSE_MANIFEST_JSON_KEYS_JSON="$("$PY" -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "${PAUSE_MANIFEST_JSON_KEYS[@]}")"
export PAUSE_MANIFEST_JSON_KEYS_JSON

"$PY" <<'PY'
import json
import os

out_path = os.environ["OUT_PATH"]
expected_keys = json.loads(os.environ["PAUSE_MANIFEST_JSON_KEYS_JSON"])

manifest = {
    "aws_account_id": os.environ["aws_account_id"],
    "regions": ["eu-west-1", "us-east-1"],
    "video_bucket_name": os.environ["video_bucket_name"],
    "student_bucket_name": os.environ["student_bucket_name"],
    "teacher_bucket_name": os.environ["teacher_bucket_name"],
    "api_endpoint": os.environ["api_endpoint"],
    "user_pool_id": os.environ["user_pool_id"],
    "student_user_pool_client_id": os.environ["student_user_pool_client_id"],
    "teacher_user_pool_client_id": os.environ["teacher_user_pool_client_id"],
    "cognito_hosted_ui_domain": os.environ["cognito_hosted_ui_domain"],
    "rds_db_host": os.environ["rds_db_host"],
    "rds_snapshot_identifier": os.environ["rds_snapshot_identifier"],
    "github_env_checklist": [
        "AWS_DEPLOY_ROLE_ARN",
        "COGNITO_DOMAIN_PREFIX",
        "ROUTE53_HOSTED_ZONE_ID",
        "STUDENT_WEB_DOMAIN",
        "TEACHER_WEB_DOMAIN",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "COGNITO_RDS_VERIFY_TEST_PASSWORD",
        "COGNITO_RDS_VERIFY_JWT",
        "COGNITO_RDS_VERIFY_TEST_USERNAME",
        "COGNITO_RDS_VERIFY_TEST_PASSWORD_ALT",
        "COGNITO_RDS_VERIFY_TEST_USERNAME_ALT",
        "COGNITO_RDS_VERIFY_TEST_PASSWORD_STUDENT",
        "COGNITO_RDS_VERIFY_TEST_USERNAME_STUDENT",
    ],
}

assert list(manifest.keys()) == expected_keys

with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")
PY

echo "Wrote pause manifest: $OUT_PATH"
echo ""
echo "IMPORTANT: Store this manifest outside the repository (password manager, secure drive)."
echo "It contains restore-critical infrastructure IDs. Do not commit pause-manifest.json."
