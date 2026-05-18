"""Contract tests: Deploy workflow keeps prod RDS graph and verify job wired."""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _workflow_text() -> str:
    path = _repo_root() / ".github" / "workflows" / "deploy-backend.yml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _verify_rds_reusable_text() -> str:
    path = _repo_root() / ".github" / "workflows" / "verify-rds-reusable.yml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_workflow_includes_prod_rds_job_ids() -> None:
    text = _workflow_text()
    for needle in (
        "  deploy-rds-prod:",
        "  apply-schema-prod:",
        "  verify-prod-rds:",
    ):
        assert needle in text, f"missing job block {needle!r}"


def test_deploy_backend_uses_repository_variable_for_oidc_role_not_environment_secret() -> None:
    """Backend/media/SQS deploys must not pick up a wrong per-env secret (e.g. web-only role ARN)."""
    text = _workflow_text()
    assert "secrets.AWS_DEPLOY_ROLE_ARN" not in text
    assert text.count("vars.AWS_DEPLOY_ROLE_ARN") >= 10
    pin = _job_block(text, "resolve-oidc-deploy-role", "\n  # --- Integration tests")
    assert "vars.AWS_DEPLOY_ROLE_ARN" in pin


def test_integration_http_tests_use_dev_environment_and_pinned_oidc_role_output() -> None:
    """integration-http-tests attach `environment: dev` for Cognito secrets but assume OIDC role from a no-env job."""
    text = _workflow_text()
    http_tests = _job_block(text, "integration-http-tests", "\n  # --- Dev:")
    assert re.search(r"^\s+environment:\s*dev\s*$", http_tests, re.M)
    assert "needs.resolve-oidc-deploy-role.outputs.aws_deploy_role_arn" in http_tests
    assert (
        "role-to-assume: ${{ needs.resolve-oidc-deploy-role.outputs.aws_deploy_role_arn }}"
        in http_tests
    )
    assert "deploy-backend-integ" not in text


def test_deploy_backend_prod_depends_on_rds_and_schema_and_wires_rds_stack() -> None:
    text = _workflow_text()
    start = text.index("  deploy-backend-prod:")
    end = text.index("    steps:", start)
    block = text[start:end]
    assert "      - deploy-rds-prod" in block
    assert "      - apply-schema-prod" in block
    assert "needs.deploy-rds-prod.result == 'success'" in block
    assert "needs.apply-schema-prod.result == 'success'" in block
    assert "RDS_STACK_NAME: StreamMyCourse-Rds-prod" in block


def test_deploy_backend_dev_depends_on_rds_and_schema_and_wires_rds_stack() -> None:
    text = _workflow_text()
    start = text.index("  deploy-backend-dev:")
    end = text.index("    steps:", start)
    block = text[start:end]
    # needs may be array format: [gate, deploy-rds-dev, apply-schema-dev]
    assert "deploy-rds-dev" in block
    assert "apply-schema-dev" in block
    assert "needs.deploy-rds-dev.result == 'success'" in block
    assert "needs.apply-schema-dev.result == 'success'" in block
    assert "RDS_STACK_NAME: StreamMyCourse-Rds-dev" in block


def _job_block(text: str, job_id: str, next_marker: str) -> str:
    start = text.index(f"  {job_id}:")
    next_job = text.index(next_marker, start)
    return text[start:next_job]


def test_verify_dev_rds_wires_only_dev_stacks_and_reusable_environment_dev() -> None:
    text = _workflow_text()
    block = _job_block(text, "verify-dev-rds", "\n  # --- Stage 4:")
    assert "integration-http-tests" in block
    assert "uses: ./.github/workflows/verify-rds-reusable.yml" in block
    # Job cannot use `environment:` with `uses:` (actionlint). `github_environment` input is different.
    assert re.search(r"^    environment:\s*dev\s*$", block, re.M) is None
    assert "COGNITO_RDS_VERIFY_TEST_PASSWORD: ${{ secrets.COGNITO_RDS_VERIFY_TEST_PASSWORD }}" in block
    assert "COGNITO_RDS_VERIFY_JWT: ${{ secrets.COGNITO_RDS_VERIFY_JWT }}" in block
    assert "github_environment: dev" in block
    assert "aws_region: eu-west-1" in block
    assert "api_stack_name: streammycourse-api" in block
    assert "auth_stack_name: StreamMyCourse-Auth-dev" in block
    assert "aws_deploy_role_arn: ${{ vars.AWS_DEPLOY_ROLE_ARN }}" in block
    assert "secrets.INTEG_DEV_COGNITO_" not in block
    assert "vars.INTEG_DEV_COGNITO_" not in block
    assert "StreamMyCourse-Auth-prod" not in block


def test_verify_prod_rds_wires_only_prod_stacks_and_reusable_environment_prod() -> None:
    text = _workflow_text()
    block = _job_block(text, "verify-prod-rds", "\n  deploy-web-prod:")
    assert "uses: ./.github/workflows/verify-rds-reusable.yml" in block
    assert re.search(r"^    environment:\s*prod\s*$", block, re.M) is None
    assert "COGNITO_RDS_VERIFY_TEST_PASSWORD: ${{ secrets.COGNITO_RDS_VERIFY_TEST_PASSWORD }}" in block
    assert "COGNITO_RDS_VERIFY_JWT: ${{ secrets.COGNITO_RDS_VERIFY_JWT }}" in block
    assert "github_environment: prod" in block
    assert "aws_region: eu-west-1" in block
    assert "api_stack_name: StreamMyCourse-Api-prod" in block
    assert "video_stack_name: StreamMyCourse-Video-prod" in block
    assert "auth_stack_name: StreamMyCourse-Auth-prod" in block
    assert "aws_deploy_role_arn: ${{ vars.AWS_DEPLOY_ROLE_ARN }}" in block
    assert "secrets.INTEG_PROD_COGNITO_" not in block
    assert "vars.INTEG_PROD_COGNITO_" not in block
    assert "StreamMyCourse-Auth-dev" not in block


def test_verify_rds_reusable_uses_unified_environment_secret_names() -> None:
    text = _verify_rds_reusable_text()
    assert "workflow_call:" in text
    assert "COGNITO_RDS_VERIFY_TEST_PASSWORD:" in text  # workflow_call secrets + step env
    assert "COGNITO_RDS_VERIFY_JWT:" in text
    assert "environment: ${{ inputs.github_environment }}" in text
    assert "inputs.aws_deploy_role_arn" in text
    assert "secrets.COGNITO_RDS_VERIFY_TEST_PASSWORD" in text
    assert "secrets.COGNITO_RDS_VERIFY_JWT" in text
    assert "vars.COGNITO_RDS_VERIFY_TEST_USERNAME" in text
    assert "secrets.COGNITO_RDS_VERIFY_DEV_TEST_PASSWORD" not in text
    assert "secrets.COGNITO_RDS_VERIFY_PROD_TEST_PASSWORD" not in text


def test_verify_rds_reusable_has_no_literal_environment_specific_stack_names() -> None:
    """Reusable workflow must stay decoupled: stack names only via inputs (no dev/prod literals here)."""
    text = _verify_rds_reusable_text()
    for forbidden in (
        "StreamMyCourse-Auth-dev",
        "StreamMyCourse-Auth-prod",
        "StreamMyCourse-Video-dev",
        "StreamMyCourse-Video-prod",
        "StreamMyCourse-Api-prod",
        "streammycourse-api",
        "StreamMyCourse-Catalog-dev",
        "StreamMyCourse-Catalog-prod",
    ):
        assert forbidden not in text, f"unexpected coupling literal {forbidden!r} in verify-rds-reusable.yml"


def test_deploy_rds_prod_waits_for_dev_edge() -> None:
    text = _workflow_text()
    start = text.index("  deploy-rds-prod:")
    end = text.index("    steps:", start)
    block = text[start:end]
    assert "deploy-edge-dev" in block
    assert "needs.deploy-edge-dev.result == 'success'" in block


def _deploy_backend_sh_text() -> str:
    path = _repo_root() / "scripts" / "deploy-backend.sh"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_backend_sh_invokes_deploy_payments_for_dev_and_prod() -> None:
    text = _deploy_backend_sh_text()
    assert "deploy-payments.sh" in text
    assert 'case "$ENV" in' in text
    assert "dev | prod)" in text
    assert "StreamMyCourse-Payments-${ENV}" in text
    assert "BillingEdgeLambdaArn" in text
    assert "BILLING_PARAM_OVERRIDES" in text


def test_deploy_backend_sh_passes_billing_fulfillment_alert_email_to_payments() -> None:
    text = _deploy_backend_sh_text()
    assert "export BILLING_FULFILLMENT_ALERT_EMAIL" in text
    payments_block = text[text.index("deploy-payments.sh") : text.index("PAYMENTS_STACK=")]
    assert "BILLING_FULFILLMENT_ALERT_EMAIL" in payments_block


def test_deploy_backend_sh_passes_billing_edge_arn_to_api_stack() -> None:
    text = _deploy_backend_sh_text()
    assert '"BillingEdgeLambdaArn=${BILLING_EDGE_ARN}"' in text
    assert "BillingFulfillmentQueueUrl=" not in text
    assert "${BILLING_PARAM_OVERRIDES[@]}" in text


def test_api_stack_exposes_billing_and_paytabs_webhook_routes() -> None:
    text = (_repo_root() / "infrastructure" / "templates" / "api-stack.yaml").read_text(
        encoding="utf-8"
    )
    assert "BillingEdgeLambdaArn:" in text
    assert "PathPart: checkout-session" in text
    assert "PathPart: paytabs" in text
    assert "/webhooks/payments/paytabs" in text
    assert "BillingCheckoutSessionPostMethod:" in text
    assert "WebhooksPaytabsPostMethod:" in text
    assert "AuthorizationType: NONE" in text
    assert "${BillingEdgeLambdaArn}/invocations" in text


def test_deploy_workflow_dev_maps_paytabs_env_for_payments_stack() -> None:
    text = _workflow_text()
    block = _job_block(text, "deploy-backend-dev", "\n  deploy-web-dev:")
    deploy_dev = block[block.index("- name: Deploy dev") :]
    assert "PAYTABS_SERVER_KEY: ${{ secrets.PAYTABS_SERVER_KEY }}" in deploy_dev
    assert "PAYTABS_PROFILE_ID: ${{ vars.PAYTABS_PROFILE_ID }}" in deploy_dev
    assert "PAYTABS_API_DOMAIN: ${{ vars.PAYTABS_API_DOMAIN }}" in deploy_dev
    assert "PAYMENT_PROVIDER: ${{ vars.PAYMENT_PROVIDER }}" in deploy_dev
    assert "PAYTABS_USE_MOCK: ${{ vars.PAYTABS_USE_MOCK }}" in deploy_dev


def test_deploy_workflow_prod_passes_paytabs_secret_arn_only() -> None:
    text = _workflow_text()
    block = _job_block(text, "deploy-backend-prod", "\n  # Prod-only")
    deploy_prod = block[block.index("- name: Deploy prod") :]
    assert "PAYTABS_SECRET_ARN: ${{ secrets.PAYTABS_SECRET_ARN }}" in deploy_prod
    assert "PAYTABS_SERVER_KEY" not in deploy_prod
    assert "aws secretsmanager describe-secret" in deploy_prod
    assert "--secret-id streammycourse/paytabs/prod" in deploy_prod


def test_deploy_workflow_upserts_paytabs_placeholder_secrets_dev_and_prod() -> None:
    text = _workflow_text()
    dev_block = _job_block(text, "deploy-backend-dev", "\n  deploy-web-dev:")
    prod_block = _job_block(text, "deploy-backend-prod", "\n  # Prod-only")
    assert "Ensure PayTabs placeholder secret (dev)" in dev_block
    assert "streammycourse/paytabs/dev" in dev_block
    assert "aws secretsmanager create-secret" in dev_block
    assert "describe-secret" in dev_block
    assert "Ensure PayTabs placeholder secret (prod)" in prod_block
    assert "streammycourse/paytabs/prod" in prod_block
    assert "aws secretsmanager create-secret" in prod_block
