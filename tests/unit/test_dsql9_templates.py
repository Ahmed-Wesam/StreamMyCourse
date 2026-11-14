"""DSQL-9 S5 — api/auth/payments templates are DSQL-only (no RDS surface)."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_TEMPLATES = _REPO / "infrastructure" / "templates"

_FORBIDDEN_IN_APP_STACKS = (
    "VpcConfig",
    "DB_HOST",
    "DB_SECRET_ARN",
    "RdsStackName",
    "UseRds",
    "UseDsql",
    "AWSLambdaVPCAccessExecutionRole",
)


def _read(name: str) -> str:
    return (_TEMPLATES / name).read_text(encoding="utf-8")


def test_app_stacks_do_not_mention_rds_or_vpc() -> None:
    for stack in ("api-stack.yaml", "auth-stack.yaml", "payments-stack.yaml"):
        text = _read(stack)
        for token in _FORBIDDEN_IN_APP_STACKS:
            assert token not in text, f"{stack} must not contain {token!r}"


def test_rds_templates_removed() -> None:
    for name in ("rds-stack.yaml", "rds-query-stack.yaml"):
        assert not (_TEMPLATES / name).is_file(), f"{name} should be deleted"


def test_auth_user_profile_sync_gated_on_dsql_endpoint_only() -> None:
    text = _read("auth-stack.yaml")
    assert "HasRdsStackName" not in text
    block = text.split("ShouldDeployUserProfileSync", 1)[1][:500]
    assert "HasDsqlEndpoint" in block
    assert "HasRdsStackName" not in block
    assert "UserProfileSyncLambda:" in text
    assert "Condition: ShouldDeployUserProfileSync" in text


def test_dsql_stack_retains_cluster() -> None:
    text = _read("dsql-stack.yaml")
    assert re.search(r"^\s+DeletionPolicy:\s+Retain\s*$", text, re.MULTILINE)
    assert "DeletionProtectionEnabled: true" in text


def test_api_catalog_lambda_timeout_20_authorizer_10() -> None:
    """DSQL-9 S7: CatalogLambda timeout 20s (under API GW 29s); authorizer stays 10."""
    text = _read("api-stack.yaml")
    catalog = re.search(
        r"(?ms)^\s+CatalogLambda:\s*\n.*?(?=^\s+\w+:\s*\n\s+Type:)",
        text,
    )
    assert catalog, "CatalogLambda resource not found"
    assert re.search(r"^\s+Timeout:\s+20\s*$", catalog.group(0), re.MULTILINE)

    authorizer = re.search(
        r"(?ms)^\s+TokenAuthorizerLambda:\s*\n.*?(?=^\s+\w+:\s*\n\s+Type:)",
        text,
    )
    assert authorizer, "TokenAuthorizerLambda resource not found"
    assert re.search(r"^\s+Timeout:\s+10\s*$", authorizer.group(0), re.MULTILINE)
