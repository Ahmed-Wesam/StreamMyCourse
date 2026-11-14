"""Contract tests: Deploy workflow (DSQL-9 S6 — no RDS jobs, unified Cognito verify names)."""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workflow_text() -> str:
    path = _repo_root() / ".github" / "workflows" / "deploy-backend.yml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_workflow_has_no_waf_jobs() -> None:
    text = _workflow_text()
    for forbidden in (
        "deploy-api-waf-dev",
        "deploy-edge-waf-dev",
        "deploy-api-waf-prod",
        "deploy-edge-waf-prod",
        "deploy-api-waf.sh",
        "deploy-edge-waf.sh",
    ):
        assert forbidden not in text, f"unexpected WAF reference {forbidden!r}"


def test_waf_templates_and_deploy_scripts_removed() -> None:
    root = _repo_root()
    for rel in (
        "infrastructure/templates/api-waf-stack.yaml",
        "infrastructure/templates/edge-waf-stack.yaml",
        "scripts/deploy-api-waf.sh",
        "scripts/deploy-edge-waf.sh",
    ):
        assert not (root / rel).is_file(), f"WAF artifact should be removed: {rel}"


def test_infrastructure_readme_does_not_list_waf_templates() -> None:
    readme = (_repo_root() / "infrastructure" / "README.md").read_text(encoding="utf-8")
    for forbidden in ("api-waf-stack.yaml", "edge-waf-stack.yaml"):
        assert forbidden not in readme, f"infrastructure/README.md must not list {forbidden!r}"


def test_delete_waf_stacks_cleanup_script_present() -> None:
    path = _repo_root() / "scripts" / "delete-waf-stacks.sh"
    assert path.is_file(), "missing scripts/delete-waf-stacks.sh (documented in ImplementationHistory.md)"


def test_deploy_workflow_omits_rds_and_verify_jobs() -> None:
    text = _workflow_text()
    for forbidden in (
        "  deploy-rds-prod:",
        "  apply-schema-prod:",
        "  deploy-api-dsql:",
        "  verify-prod-rds:",
    ):
        assert forbidden not in text, f"removed job still present: {forbidden!r}"


def test_verify_rds_reusable_workflow_removed() -> None:
    path = _repo_root() / ".github" / "workflows" / "verify-rds-reusable.yml"
    assert not path.is_file(), "verify-rds-reusable.yml must be deleted (DSQL-9 S6)"


def test_deploy_workflow_uses_cognito_verify_secret_names() -> None:
    text = _workflow_text()
    assert "COGNITO_VERIFY_" in text
    assert "COGNITO_RDS_VERIFY_" not in text


def test_removed_rds_deploy_scripts_absent() -> None:
    root = _repo_root()
    for rel in (
        "scripts/deploy-rds-stack.sh",
        "scripts/deploy-rds-query-stack.sh",
        "scripts/sync-rds-secret-after-restore.sh",
    ):
        assert not (root / rel).is_file(), f"RDS script should be removed: {rel}"


def test_ensure_ci_verify_cognito_user_script_present() -> None:
    root = _repo_root()
    assert (root / "scripts" / "ensure-ci-verify-cognito-user.sh").is_file()
    assert not (root / "scripts" / "ensure-ci-rds-verify-cognito-user.sh").is_file()


def test_deploy_backend_sh_has_no_dsql_preview_lane() -> None:
    text = (_repo_root() / "scripts" / "deploy-backend.sh").read_text(encoding="utf-8")
    assert "DSQL_PREVIEW" not in text
    assert "StreamMyCourse-Api-dsql" not in text


def test_infrastructure_deploy_ps1_no_rds_template_or_rds_stack_name() -> None:
    text = (_repo_root() / "infrastructure" / "deploy.ps1").read_text(encoding="utf-8")
    assert '"rds"' not in text
    assert "RdsStackName" not in text
    assert "DsqlEndpoint" in text


def test_deploy_backend_uses_repository_variable_for_oidc_role_not_environment_secret() -> None:
    """Backend/media/SQS deploys must not pick up a wrong per-env secret (e.g. web-only role ARN)."""
    text = _workflow_text()
    assert "secrets.AWS_DEPLOY_ROLE_ARN" not in text
    assert text.count("vars.AWS_DEPLOY_ROLE_ARN") >= 8
    pin = _job_block(text, "resolve-oidc-deploy-role", "\n  deploy-dev-stage:")
    assert "vars.AWS_DEPLOY_ROLE_ARN" in pin


def test_integration_http_tests_target_dev_with_prod_cognito_secrets() -> None:
    """Dev API is the gate. Cognito passwords stay on the prod GitHub environment."""
    text = _workflow_text()
    http_tests = _job_block(text, "integration-http-tests", "\n  deploy-web-prod:")
    assert re.search(r"^\s+environment:\s*prod\s*$", http_tests, re.M)
    assert "needs.resolve-oidc-deploy-role.outputs.aws_deploy_role_arn" in http_tests
    assert (
        "role-to-assume: ${{ needs.resolve-oidc-deploy-role.outputs.aws_deploy_role_arn }}"
        in http_tests
    )
    assert "deploy-dev-stage" in http_tests
    assert "StreamMyCourse-Api-dev" in http_tests
    assert "StreamMyCourse-DevVideo-dev" in http_tests
    assert "StreamMyCourse-Auth-dev" in http_tests
    assert "StreamMyCourse-Dsql-dev" in http_tests
    assert "INTEGRATION_ALLOW_PROD_CLEANUP" not in http_tests
    assert "cfuhjrrzy65ngud25rdqqso5t4" in http_tests
    assert "streammycourse-api" not in http_tests
    assert "deploy-backend-integ" not in text


def test_deploy_workflow_has_no_dev_jobs() -> None:
    text = _workflow_text()
    for forbidden in (
        "deploy-edge-dev",
        "deploy-rds-dev",
        "deploy-backend-dev",
        "verify-dev-rds",
        "deploy-web-dev",
        "streammycourse-api",
    ):
        assert forbidden not in text, f"dev job or stack reference must be removed: {forbidden!r}"


def test_deploy_backend_prod_depends_on_dev_tests_and_edge() -> None:
    text = _workflow_text()
    start = text.index("  deploy-backend-prod:")
    end = text.index("    steps:", start)
    block = text[start:end]
    assert "      - gate" in block
    assert "      - integration-http-tests" in block
    assert "      - deploy-edge-prod" in block
    assert "deploy-rds-prod" not in block
    assert "apply-schema-prod" not in block
    assert "RDS_STACK_NAME" not in block


def _job_block(text: str, job_id: str, next_marker: str) -> str:
    start = text.index(f"  {job_id}:")
    next_job = text.index(next_marker, start)
    return text[start:next_job]


def test_spa_deploy_jobs_need_integration_http_tests_not_verify_rds() -> None:
    text = _workflow_text()
    for job_id in ("deploy-web-prod", "deploy-teacher-web-prod"):
        start = text.index(f"  {job_id}:")
        tail = text[start:]
        m = re.search(r"\n  [a-z][\w-]*:", tail[len(f"  {job_id}:") :])
        end = start + len(f"  {job_id}:") + (m.start() if m else len(tail))
        block = text[start:end]
        assert "integration-http-tests" in block
        assert "verify-prod-rds" not in block


def _deploy_backend_sh_text() -> str:
    path = _repo_root() / "scripts" / "deploy-backend.sh"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_backend_prod_packages_cognito_pre_signup_lambda() -> None:
    text = _workflow_text()
    block = _job_block(text, "deploy-backend-prod", "\n  integration-http-tests:")
    assert "Package and upload Cognito PreSignUp Lambda (prod)" in block
    assert "cognito_pre_signup_pkg_prod" in block
    assert "cognito-pre-signup-prod-" in block
    assert "CognitoPreSignUpCodeS3Bucket=${{ steps.cognito_pre_signup_pkg_prod.outputs.bucket }}" in block
    assert "Package and upload Cognito custom email sender Lambda (prod)" in block
    assert "cognito_custom_email_pkg_prod" in block
    assert "Ensure Zoho SMTP secret (prod)" in block
    assert "ZohoSmtpSecretArn=${{ steps.zoho_smtp_secret_prod.outputs.arn }}" in block


def test_deploy_payments_sh_cleans_rollback_and_orphan_sqs() -> None:
    text = (_repo_root() / "scripts" / "deploy-payments.sh").read_text(encoding="utf-8")
    assert "_ensure_payments_stack_deployable" in text
    assert "ROLLBACK_COMPLETE" in text
    assert "StreamMyCourse-BillingFulfillment-DLQ-" in text
    assert "RdsStackName" not in text


def test_deploy_backend_sh_resolves_dsql_before_early_payments() -> None:
    text = _deploy_backend_sh_text()
    pay_idx = text.index("# Billing edge + fulfillment queue")
    dsql_idx = text.index("if ! _resolve_dsql_stack_outputs; then", 0, pay_idx)
    assert dsql_idx < pay_idx


def test_deploy_backend_sh_deploys_payments_before_api_stack() -> None:
    text = _deploy_backend_sh_text()
    assert "deploy-payments.sh" in text
    assert 'BILLING_PARAM_OVERRIDES=("BillingEdgeLambdaArn=${BILLING_EDGE_ARN}")' in text
    assert "StreamMyCourse-Payments-${ENV}" in text
    assert "delete-stack" not in text
    assert "streammycourse/hyperpay" not in text
    assert "${BILLING_PARAM_OVERRIDES[@]}" in text
    assert "Updating payments stack with catalog invoke + billing return URLs" in text


def test_deploy_backend_sh_passes_billing_teacher_sub_to_api_stack() -> None:
    text = _deploy_backend_sh_text()
    assert 'export BILLING_TEACHER_SUB="${BILLING_TEACHER_SUB:-}"' in text
    assert '"BillingTeacherSub=${BILLING_TEACHER_SUB:-}"' in text


def test_api_stack_exposes_billing_and_hyperpay_webhook_routes() -> None:
    text = (_repo_root() / "infrastructure" / "templates" / "api-stack.yaml").read_text(
        encoding="utf-8"
    )
    assert "BillingEdgeLambdaArn:" in text
    assert "PathPart: checkout-session" in text
    assert "PathPart: checkout-status" in text
    assert "PathPart: hyperpay" in text
    assert "/webhooks/payments/hyperpay" in text
    assert "BillingCheckoutSessionPostMethod:" in text
    assert "BillingCheckoutStatusPostMethod:" in text
    assert "WebhooksHyperpayPostMethod:" in text
    assert "AuthorizationType: NONE" in text
    assert "${BillingEdgeLambdaArn}/invocations" in text


def test_deploy_workflow_prod_provisions_hyperpay_secret() -> None:
    text = _workflow_text()
    block = _job_block(text, "deploy-backend-prod", "\n  integration-http-tests:")
    assert "Ensure HyperPay secret (prod)" in block
    assert "ensure-hyperpay-secret.sh" in block
    assert "HYPERPAY_ACCESS_TOKEN" in block
    assert "HYPERPAY_SECRET_ARN" in block
    assert "streammycourse/hyperpay/prod" in block
    assert "BILLING_TEACHER_SUB: ${{ vars.BILLING_TEACHER_SUB }}" in block
    assert "PAYMENT_PROVIDER: ${{ vars.PAYMENT_PROVIDER }}" in block
