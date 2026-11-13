"""DSQL-8 S3: template and deploy-order contracts."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]


def test_auth_sync_condition_allows_dsql_without_rds() -> None:
    text = (_REPO / "infrastructure/templates/auth-stack.yaml").read_text(encoding="utf-8")
    assert "HasDsqlEndpoint" in text
    assert "ShouldDeployUserProfileSync: !And" in text
    assert "HasRdsStackName" in text
    block = text.split("ShouldDeployUserProfileSync", 1)[1][:400]
    assert "HasDsqlEndpoint" in block
    assert "UseDsql" in text
    assert "DSQL_ENDPOINT" in text


def test_payments_and_auth_vpc_config_gated_on_use_rds() -> None:
    pay = (_REPO / "infrastructure/templates/payments-stack.yaml").read_text(encoding="utf-8")
    auth = (_REPO / "infrastructure/templates/auth-stack.yaml").read_text(encoding="utf-8")
    assert "VpcConfig: !If" in pay
    assert "UseRds" in pay
    assert "VpcConfig: !If" in auth


def test_workflow_auth_before_deploy_backend() -> None:
    wf = (_REPO / ".github/workflows/deploy-backend.yml").read_text(encoding="utf-8")
    auth_pos = wf.index("Deploy auth (prod)")
    deploy_pos = wf.index("./scripts/deploy-backend.sh prod")
    assert auth_pos < deploy_pos


def test_deploy_backend_payments_before_api_on_prod_dsql() -> None:
    sh = (_REPO / "scripts/deploy-backend.sh").read_text(encoding="utf-8")
    pre_api = sh.index("Pre-API: updating payments stack")
    api_deploy = sh.index('_deploy_api_stack "phase A"')
    assert pre_api < api_deploy
