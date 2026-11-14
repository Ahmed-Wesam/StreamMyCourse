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


def _register_db_tx() -> None:
    if "db_tx" in sys.modules:
        return
    db_tx_path = ROOT / "infrastructure/lambda/catalog/services/common/db_tx.py"
    spec = importlib.util.spec_from_file_location("db_tx", db_tx_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["db_tx"] = mod


def _load_module(name: str, path: Path):
    if path.name == "fulfillment_repo.py":
        _register_db_tx()
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
    factory = sync_repo_mod.build_connection_factory(dsql_endpoint=endpoint)
    factory()
    fake_dsql_connect.assert_called_once_with(endpoint)


def test_cognito_sync_raises_when_both_db_hosts_set(
    fake_dsql_connect: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    sync_repo_mod = _load_module(
        "cognito_sync_repo_both",
        ROOT / "infrastructure/lambda/cognito_user_profile_sync/repo.py",
    )
    monkeypatch.setenv("DB_HOST", "rds.host")
    with pytest.raises(RuntimeError, match="DSQL_ENDPOINT only"):
        sync_repo_mod.build_connection_factory(
            dsql_endpoint="cluster.dsql.eu-west-1.on.aws",
        )
    fake_dsql_connect.assert_not_called()


def test_deploy_backend_sync_package_uses_sync_requirements() -> None:
    workflow = ROOT / ".github/workflows/deploy-backend.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "cognito_user_profile_sync/requirements.txt" in text
    block_start = text.index("Package and upload Cognito user profile sync Lambda")
    block = text[block_start : block_start + 2500]
    assert "dsql_connect.py" in block


def test_billing_fulfillment_raises_when_both_db_hosts_set(
    fake_dsql_connect: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    fulfill_mod = _load_module(
        "fulfillment_repo_both",
        ROOT / "infrastructure/lambda/billing_fulfillment/fulfillment_repo.py",
    )
    monkeypatch.setenv("DB_SECRET_ARN", "arn:secret")
    with pytest.raises(RuntimeError, match="DSQL_ENDPOINT only"):
        fulfill_mod.build_connection_factory(
            dsql_endpoint="cluster.dsql.eu-west-1.on.aws",
        )
    fake_dsql_connect.assert_not_called()


def test_deploy_payments_sh_copies_db_tx_into_fulfillment_zip() -> None:
    text = (ROOT / "scripts/deploy-payments.sh").read_text(encoding="utf-8")
    assert "services/common/db_tx.py" in text
    assert 'FULFILL_BUILD/db_tx.py' in text or '"$FULFILL_BUILD/db_tx.py"' in text


def test_billing_fulfillment_build_connection_factory_uses_dsql(fake_dsql_connect: MagicMock) -> None:
    fulfill_mod = _load_module(
        "fulfillment_repo",
        ROOT / "infrastructure/lambda/billing_fulfillment/fulfillment_repo.py",
    )
    endpoint = "cluster.dsql.eu-west-1.on.aws"
    factory = fulfill_mod.build_connection_factory(dsql_endpoint=endpoint)
    factory()
    fake_dsql_connect.assert_called_once_with(endpoint)
