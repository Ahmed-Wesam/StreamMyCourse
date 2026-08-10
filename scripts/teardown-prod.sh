#!/usr/bin/env bash
# Teardown prod CloudFormation stacks (pause/shutdown Phase 2).
#
# Usage:
#   ./scripts/teardown-prod.sh [--dry-run] [--confirm] [--skip-missing] [--manifest-out PATH]
#
# Mutating operations require --confirm. Use --dry-run to preview without changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=scripts/lib/prod_pause_constants.sh
source "$SCRIPT_DIR/lib/prod_pause_constants.sh"

DRY_RUN=false
CONFIRM=false
SKIP_MISSING=false
MANIFEST_OUT=""

RDS_STACK_NAME="StreamMyCourse-Rds-prod"
RDS_DB_INSTANCE_ID="streammycourse-prod"
RDS_REGION="eu-west-1"

usage() {
  echo "Usage: $0 [--dry-run] [--confirm] [--skip-missing] [--manifest-out PATH]" >&2
  echo "  --dry-run         Preview teardown steps without mutating AWS resources." >&2
  echo "  --confirm         Required for mutating operations; prompts for AWS account ID." >&2
  echo "  --skip-missing    Continue when a stack is absent instead of failing." >&2
  echo "  --manifest-out    Export pause manifest to PATH before stack deletes." >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
  --dry-run)
    DRY_RUN=true
    ;;
  --confirm)
    CONFIRM=true
    ;;
  --skip-missing)
    SKIP_MISSING=true
    ;;
  --manifest-out)
    shift
    MANIFEST_OUT="${1:?--manifest-out requires a path}"
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

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
echo "AWS account: $ACCOUNT_ID"

refuse_without_confirm() {
  echo "Refusing mutating operation without --confirm (use --dry-run to preview)." >&2
  exit 1
}

if [[ -n "$MANIFEST_OUT" ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would export pause manifest to: $MANIFEST_OUT"
  else
    if [[ "$CONFIRM" != true ]]; then
      refuse_without_confirm
    fi
    echo "Exporting pause manifest to: $MANIFEST_OUT"
    "$SCRIPT_DIR/export-pause-manifest.sh" --out "$MANIFEST_OUT"
  fi
fi

if [[ "$DRY_RUN" != true && "$CONFIRM" != true ]]; then
  refuse_without_confirm
fi

if [[ "$CONFIRM" == true && "$DRY_RUN" != true ]]; then
  echo -n "Type AWS account ID ($ACCOUNT_ID) to confirm prod teardown: "
  read -r typed_account
  if [[ "$typed_account" != "$ACCOUNT_ID" ]]; then
    echo "Account ID mismatch. Aborting." >&2
    exit 1
  fi
fi

stack_exists() {
  local stack="$1"
  local region="$2"
  aws cloudformation describe-stacks --stack-name "$stack" --region "$region" >/dev/null 2>&1
}

run_waf_teardown() {
  local waf_script="$ROOT/$TEARDOWN_WAF_SCRIPT"
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Step 0: would run $TEARDOWN_WAF_SCRIPT"
    return 0
  fi
  echo "Step 0: running $TEARDOWN_WAF_SCRIPT"
  bash "$waf_script"
}

disable_rds_deletion_protection() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would disable deletion protection on RDS instance $RDS_DB_INSTANCE_ID ($RDS_REGION) and wait until available"
    return 0
  fi
  if ! aws rds describe-db-instances \
    --db-instance-identifier "$RDS_DB_INSTANCE_ID" \
    --region "$RDS_REGION" >/dev/null 2>&1; then
    echo "RDS instance $RDS_DB_INSTANCE_ID not found; skipping deletion protection disable."
    return 0
  fi
  echo "Disabling deletion protection on RDS instance $RDS_DB_INSTANCE_ID ($RDS_REGION)..."
  aws rds modify-db-instance \
    --db-instance-identifier "$RDS_DB_INSTANCE_ID" \
    --no-deletion-protection \
    --apply-immediately \
    --region "$RDS_REGION"
  echo "Waiting for RDS instance $RDS_DB_INSTANCE_ID to become available..."
  aws rds wait db-instance-available \
    --db-instance-identifier "$RDS_DB_INSTANCE_ID" \
    --region "$RDS_REGION"
}

delete_stack_entry() {
  local entry="$1"
  local stack="${entry%%:*}"
  local region="${entry##*:}"

  if ! stack_exists "$stack" "$region"; then
    if [[ "$SKIP_MISSING" == true ]]; then
      echo "Skip $stack (not found in $region)"
      return 0
    fi
    echo "Stack $stack not found in $region (use --skip-missing to continue)." >&2
    exit 1
  fi

  if [[ "$stack" == "$RDS_STACK_NAME" ]]; then
    disable_rds_deletion_protection
  fi

  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would delete stack $stack ($region)"
    return 0
  fi

  echo "Deleting stack $stack ($region)..."
  aws cloudformation delete-stack --stack-name "$stack" --region "$region"
  aws cloudformation wait stack-delete-complete --stack-name "$stack" --region "$region"
  echo "Deleted $stack"
}

delete_stack_list() {
  local label="$1"
  shift
  local stacks=("$@")
  echo ""
  echo "=== $label (account $ACCOUNT_ID) ==="
  for entry in "${stacks[@]}"; do
    delete_stack_entry "$entry"
  done
}

run_waf_teardown
delete_stack_list "Primary prod stacks" "${TEARDOWN_STACKS[@]}"
delete_stack_list "Legacy prod stacks" "${TEARDOWN_LEGACY_STACKS[@]}"

echo ""
if [[ "$DRY_RUN" == true ]]; then
  echo "Dry-run complete (account $ACCOUNT_ID). No resources were changed."
else
  echo "Prod teardown complete (account $ACCOUNT_ID)."
fi
