#!/usr/bin/env bash
# Shared prod pause/teardown constants. Sourced by teardown-prod.sh and restore-prod.sh.
#
# Teardown order matches infrastructure/docs/prod-shutdown-restore-runbook.md (reverse deploy deps).

# Step 0: disassociate and delete WAF stacks (no-op if absent).
TEARDOWN_WAF_SCRIPT="scripts/delete-waf-stacks.sh"

# Ordered CloudFormation stack deletes after WAF cleanup. Format: "StackName:region"
TEARDOWN_STACKS=(
  "StreamMyCourse-Api-prod:eu-west-1"
  "StreamMyCourse-Auth-prod:eu-west-1"
  "StreamMyCourse-VideoProviderEdge-prod:eu-west-1"
  "StreamMyCourse-Payments-prod:eu-west-1"
  "StreamMyCourse-MediaCleanup-prod:eu-west-1"
  "StreamMyCourse-RdsQuery-prod:eu-west-1"
  "StreamMyCourse-Rds-prod:eu-west-1"
  "StreamMyCourse-Video-prod:eu-west-1"
  "StreamMyCourse-EdgeHosting-prod:us-east-1"
  "StreamMyCourse-ArtifactJanitor-prod:eu-west-1"
)

# Legacy split stacks (delete if present, after primary prod stacks).
TEARDOWN_LEGACY_STACKS=(
  "StreamMyCourse-Web-prod:us-east-1"
  "StreamMyCourse-TeacherWeb-prod:us-east-1"
  "StreamMyCourse-Cert-prod:us-east-1"
)

# JSON object keys written by export-pause-manifest.sh (values only; no secrets).
PAUSE_MANIFEST_JSON_KEYS=(
  "aws_account_id"
  "regions"
  "video_bucket_name"
  "student_bucket_name"
  "teacher_bucket_name"
  "api_endpoint"
  "user_pool_id"
  "student_user_pool_client_id"
  "teacher_user_pool_client_id"
  "cognito_hosted_ui_domain"
  "rds_db_host"
  "rds_snapshot_identifier"
  "github_env_checklist"
)
