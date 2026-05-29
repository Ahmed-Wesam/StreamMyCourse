#!/usr/bin/env bash
# Delete StreamMyCourse WAF CloudFormation stacks (if they exist).
# Disassociates Web ACLs via stack delete; safe to re-run when stacks are already gone.
set -euo pipefail

delete_if_exists() {
  local stack="$1"
  local region="$2"
  if aws cloudformation describe-stacks --stack-name "$stack" --region "$region" >/dev/null 2>&1; then
    echo "Deleting stack $stack ($region)..."
    aws cloudformation delete-stack --stack-name "$stack" --region "$region"
    aws cloudformation wait stack-delete-complete --stack-name "$stack" --region "$region"
    echo "Deleted $stack"
  else
    echo "Skip $stack (not found in $region)"
  fi
}

delete_if_exists "StreamMyCourse-ApiWaf-dev" "eu-west-1"
delete_if_exists "StreamMyCourse-ApiWaf-prod" "eu-west-1"
delete_if_exists "StreamMyCourse-EdgeWaf-dev" "us-east-1"
delete_if_exists "StreamMyCourse-EdgeWaf-prod" "us-east-1"

echo "WAF stack cleanup complete."
