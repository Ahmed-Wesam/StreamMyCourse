#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v cfn-lint >/dev/null 2>&1; then
  CFN_LINT="cfn-lint"
else
  SCRIPTS_DIR="$(python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>/dev/null || true)"
  if [[ -n "$SCRIPTS_DIR" ]] && [[ -x "$SCRIPTS_DIR/cfn-lint" ]]; then
    CFN_LINT="$SCRIPTS_DIR/cfn-lint"
  else
    echo "cfn-lint not found. Install with: python -m pip install cfn-lint" >&2
    exit 1
  fi
fi

cd "$ROOT"

$CFN_LINT --config-file .cfnlintrc infrastructure/templates/api-stack.yaml
$CFN_LINT --config-file .cfnlintrc infrastructure/templates/auth-stack.yaml
$CFN_LINT --config-file .cfnlintrc infrastructure/templates/video-stack.yaml
$CFN_LINT --config-file .cfnlintrc infrastructure/templates/edge-hosting-stack.yaml
$CFN_LINT --config-file .cfnlintrc infrastructure/templates/github-deploy-role-stack.yaml
$CFN_LINT --config-file .cfnlintrc infrastructure/templates/billing-alarm.yaml
$CFN_LINT --config-file .cfnlintrc infrastructure/templates/rds-stack.yaml
$CFN_LINT --config-file .cfnlintrc infrastructure/templates/media-cleanup-stack.yaml

echo "OK cfn-lint"

