"""Deploy workflow: Aurora DSQL lane (DSQL-9 S6 — no RDS/preview jobs)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO / ".github" / "workflows" / "deploy-backend.yml"

_DSQL_JOBS = (
    "deploy-dsql-prod",
    "dsql-compat-spike",
    "apply-dsql-schema",
)

_DSQL_NEEDS: dict[str, frozenset[str]] = {
    "deploy-dsql-prod": frozenset({"gate"}),
    "dsql-compat-spike": frozenset({"gate", "deploy-dsql-prod"}),
    "apply-dsql-schema": frozenset({"gate", "dsql-compat-spike"}),
}

_PROD_NEEDS_SNAPSHOT: dict[str, frozenset[str]] = {
    "deploy-backend-prod": frozenset({"gate", "deploy-edge-prod"}),
    "integration-http-tests": frozenset(
        {"gate", "deploy-backend-prod", "resolve-oidc-deploy-role"}
    ),
    "deploy-web-prod": frozenset(
        {"gate", "integration-http-tests", "deploy-edge-prod"}
    ),
    "deploy-teacher-web-prod": frozenset(
        {"gate", "integration-http-tests", "deploy-edge-prod"}
    ),
}

_PROD_ROLE_SUFFIXES = (
    "StreamMyCourse-CatalogLambdaRole-prod",
    "StreamMyCourse-Auth-prod-UserProfileSyncLambdaRole",
    "StreamMyCourse-BillingFulfillmentRole-prod",
)

_REMOVED_JOBS = (
    "deploy-rds-prod",
    "apply-schema-prod",
    "deploy-api-dsql",
    "verify-prod-rds",
)


def _workflow_text() -> str:
    assert _WORKFLOW.is_file(), f"missing {_WORKFLOW}"
    return _WORKFLOW.read_text(encoding="utf-8")


def _job_block(text: str, job_id: str) -> str:
    marker = f"  {job_id}:"
    start = text.index(marker)
    tail = text[start + len(marker) :]
    m = re.search(r"\n  [a-z][\w-]*:", tail)
    end = start + len(marker) + (m.start() if m else len(tail))
    return text[start:end]


def _parse_needs(job_block: str) -> list[str]:
    list_match = re.search(
        r"^\s+needs:\s*\n((?:\s+- [\w-]+\n)+)",
        job_block,
        re.MULTILINE,
    )
    if list_match:
        return re.findall(r"^\s+- ([\w-]+)\s*$", list_match.group(1), re.MULTILINE)
    inline = re.search(r"^\s+needs:\s*\[([^\]]+)\]", job_block, re.MULTILINE)
    if inline:
        return [x.strip() for x in inline.group(1).split(",") if x.strip()]
    scalar = re.search(r"^\s+needs:\s*([\w-]+)\s*$", job_block, re.MULTILINE)
    if scalar:
        return [scalar.group(1)]
    pytest.fail(f"could not parse needs from job block:\n{job_block[:400]}")


def test_removed_rds_and_preview_jobs_absent() -> None:
    text = _workflow_text()
    for job_id in _REMOVED_JOBS:
        assert f"  {job_id}:" not in text, f"job {job_id!r} must be removed"


def test_dsql_jobs_exist_with_needs_graph() -> None:
    text = _workflow_text()
    for job_id in _DSQL_JOBS:
        assert f"  {job_id}:" in text, f"missing job {job_id!r}"
        needs = frozenset(_parse_needs(_job_block(text, job_id)))
        assert needs == _DSQL_NEEDS[job_id], (
            f"{job_id} needs {sorted(needs)}, want {sorted(_DSQL_NEEDS[job_id])}"
        )


def test_prod_jobs_needs_snapshot() -> None:
    text = _workflow_text()
    for job_id, expected in _PROD_NEEDS_SNAPSHOT.items():
        needs = frozenset(_parse_needs(_job_block(text, job_id)))
        assert needs == expected, f"{job_id} needs changed: {sorted(needs)}"


def test_prod_jobs_do_not_depend_on_dsql_lane() -> None:
    text = _workflow_text()
    for job_id in _PROD_NEEDS_SNAPSHOT:
        block = _job_block(text, job_id)
        for dsql_job in _DSQL_JOBS:
            assert f"- {dsql_job}" not in block
            assert f"needs.{dsql_job}" not in block


def test_deploy_backend_prod_no_rds_stack_env() -> None:
    block = _job_block(_workflow_text(), "deploy-backend-prod")
    assert "RDS_STACK_NAME" not in block
    assert "deploy-rds-prod" not in block
    assert "apply-schema-prod" not in block


def test_deploy_dsql_prod_deploys_stack() -> None:
    block = _job_block(_workflow_text(), "deploy-dsql-prod")
    assert "StreamMyCourse-Dsql-prod" in block
    assert "dsql-stack.yaml" in block


def test_dsql_compat_spike_runs_after_cluster() -> None:
    block = _job_block(_workflow_text(), "dsql-compat-spike")
    assert "dsql_compat_spike.py" in block
    assert "needs.deploy-dsql-prod.result == 'success'" in block


def test_apply_dsql_schema_runner_deps_and_admin_applier() -> None:
    block = _job_block(_workflow_text(), "apply-dsql-schema")
    assert "psycopg2-binary==2.9.9" in block
    assert "aurora-dsql-python-connector" in block
    assert "apply-dsql-schema.py" in block
    for suffix in _PROD_ROLE_SUFFIXES:
        assert suffix in block
    assert "needs.dsql-compat-spike.result == 'success'" in block


def test_cognito_sync_zip_includes_dsql_connect() -> None:
    block = _job_block(_workflow_text(), "deploy-backend-prod")
    assert "infrastructure/lambda/catalog/dsql_connect.py" in block
    assert "cognito_sync_pkg_prod" in block or "cognito-user-profile-sync" in block


def test_auth_and_payments_deploy_pass_optional_dsql_cluster_arn() -> None:
    block = _job_block(_workflow_text(), "deploy-backend-prod")
    assert "StreamMyCourse-Dsql-prod" in block
    assert "ResourceArn" in block
    assert "DsqlClusterArn" in block
    assert "Deploy auth (prod)" in block
    assert "deploy-payments" in block.lower() or "payments-stack.yaml" in block


def test_dsql_jobs_fail_workflow_without_continue_on_error() -> None:
    text = _workflow_text()
    for job_id in _DSQL_JOBS:
        block = _job_block(text, job_id)
        assert "continue-on-error" not in block, f"{job_id} must not use continue-on-error"


def test_dsql_jobs_gate_on_should_deploy() -> None:
    text = _workflow_text()
    for job_id in _DSQL_JOBS:
        block = _job_block(text, job_id)
        assert "needs.gate.outputs.should_deploy == 'true'" in block, job_id
        assert (
            "github.event_name == 'workflow_run' || github.event_name == 'workflow_dispatch'"
            in block
        ), job_id
