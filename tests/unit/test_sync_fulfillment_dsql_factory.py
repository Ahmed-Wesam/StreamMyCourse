"""DSQL connection factory branches for sync and fulfillment Lambdas."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fake_dsql_connect(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    inner_factory = MagicMock(return_value=MagicMock(name="dsql-conn"))
    build = MagicMock(return_value=inner_factory)
    mod = ModuleType("dsql_connect")
    mod.build_connection_factory = build  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "dsql_connect", mod)
    return build


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def test_cognito_sync_build_connection_factory_uses_dsql(fake_dsql_connect: MagicMock) -> None:
    sync_repo_mod = _load_module(
        "cognito_sync_repo",
        ROOT / "infrastructure/lambda/cognito_user_profile_sync/repo.py",
    )
    endpoint = "cluster.dsql.eu-west-1.on.aws"
    factory = sync_repo_mod.build_connection_factory(
        db_secret_arn="",
        db_host="",
        db_name="postgres",
        db_port=5432,
        dsql_endpoint=endpoint,
    )
    factory()
    fake_dsql_connect.assert_called_once_with(endpoint)


def test_billing_fulfillment_build_connection_factory_uses_dsql(fake_dsql_connect: MagicMock) -> None:
    fulfill_mod = _load_module(
        "fulfillment_repo",
        ROOT / "infrastructure/lambda/billing_fulfillment/fulfillment_repo.py",
    )
    endpoint = "cluster.dsql.eu-west-1.on.aws"
    factory = fulfill_mod.build_connection_factory(
        db_secret_arn="",
        db_host="",
        db_name="postgres",
        db_port=5432,
        dsql_endpoint=endpoint,
    )
    factory()
    fake_dsql_connect.assert_called_once_with(endpoint)
