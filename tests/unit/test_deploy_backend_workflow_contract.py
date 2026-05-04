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


def test_deploy_backend_prod_depends_on_rds_and_schema_and_uses_rds_env() -> None:
    text = _workflow_text()
    start = text.index("  deploy-backend-prod:")
    end = text.index("    steps:", start)
    block = text[start:end]
    assert "      - deploy-rds-prod" in block
    assert "      - apply-schema-prod" in block
    assert "needs.deploy-rds-prod.result == 'success'" in block
    assert "needs.apply-schema-prod.result == 'success'" in block
    assert "RDS_STACK_NAME: StreamMyCourse-Rds-prod" in block
    assert 'USE_RDS: "true"' in block


def _job_block(text: str, job_id: str, next_marker: str) -> str:
    start = text.index(f"  {job_id}:")
    next_job = text.index(next_marker, start)
    return text[start:next_job]


def test_verify_dev_rds_wires_only_dev_stacks_and_reusable_environment_dev() -> None:
    text = _workflow_text()
    block = _job_block(text, "verify-dev-rds", "\n  # --- Stage 4:")
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
    assert "catalog_table_name: StreamMyCourse-Catalog-prod" in block
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
