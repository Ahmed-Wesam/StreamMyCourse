"""Unit tests for catalog DSQL connection selection and factory."""

from __future__ import annotations

import logging
import sys
import time
from types import ModuleType
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

import bootstrap as bootstrap_mod
import dsql_connect
from config import AppConfig


@pytest.fixture(autouse=True)
def _clear_bootstrap_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap_mod, "_cached", {})


@pytest.fixture
def fake_aurora_module(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    calls: List[Dict[str, Any]] = []

    def _connect(**kwargs: Any) -> MagicMock:
        calls.append(dict(kwargs))
        conn = MagicMock(name="dsql-conn")
        conn.autocommit = False
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return conn

    mod = ModuleType("aurora_dsql_psycopg2")
    mod.connect = _connect  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "aurora_dsql_psycopg2", mod)
    return {"connect_calls": calls, "module": mod}


def _cfg_rds(**kwargs: Any) -> AppConfig:
    base = dict(
        video_bucket="",
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
        db_host="rds.example.com",
        db_name="smc",
        db_secret_arn="arn:aws:secretsmanager:eu-west-1:1:secret:x",
    )
    base.update(kwargs)
    return AppConfig(**base)


def _cfg_dsql(endpoint: str = "abc.dsql.eu-west-1.on.aws", **kwargs: Any) -> AppConfig:
    base = dict(
        video_bucket="",
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
        dsql_endpoint=endpoint,
    )
    base.update(kwargs)
    return AppConfig(**base)


class TestBootstrapDbSelection:
    def test_rds_only_uses_rds_factory_not_dsql(
        self, monkeypatch: pytest.MonkeyPatch, fake_aurora_module: Dict[str, Any]
    ) -> None:
        rds_called = {"n": 0}

        def _rds_factory(cfg: AppConfig) -> Any:
            rds_called["n"] += 1
            return lambda: MagicMock(name="rds")

        monkeypatch.setattr(bootstrap_mod, "_build_rds_connection_factory", _rds_factory)

        cfg = _cfg_rds()
        factory = bootstrap_mod._build_connection_factory(cfg)
        factory()

        assert rds_called["n"] == 1
        assert fake_aurora_module["connect_calls"] == []

    def test_dsql_only_calls_aurora_connect(
        self, monkeypatch: pytest.MonkeyPatch, fake_aurora_module: Dict[str, Any]
    ) -> None:
        cfg = _cfg_dsql()
        factory = bootstrap_mod._build_connection_factory(cfg)
        conn = factory()

        assert len(fake_aurora_module["connect_calls"]) == 1
        kw = fake_aurora_module["connect_calls"][0]
        assert kw["user"] == "smc_app"
        assert kw["dbname"] == "postgres"
        assert kw["host"] == cfg.dsql_endpoint
        assert conn is not None

    def test_both_rds_and_dsql_raises(self) -> None:
        cfg = _cfg_rds(dsql_endpoint="abc.dsql.eu-west-1.on.aws")
        with pytest.raises(RuntimeError, match="both.*DSQL_ENDPOINT.*DB_HOST"):
            bootstrap_mod.build_aws_deps(cfg)

    def test_neither_config_leaves_lambda_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for name in ("DB_HOST", "DB_NAME", "DB_SECRET_ARN", "DSQL_ENDPOINT"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("ALLOWED_ORIGINS", "*")
        out = bootstrap_mod.lambda_bootstrap()
        assert out[1] is None


class TestDsqlFactory:
    def test_search_path_set_on_new_connection(self, fake_aurora_module: Dict[str, Any]) -> None:
        factory = dsql_connect.build_connection_factory("host.dsql.example")
        conn = factory()
        cur = conn.cursor.return_value.__enter__.return_value
        executed = [call.args[0] for call in cur.execute.call_args_list]
        assert any("search_path" in sql and "app" in sql for sql in executed)

    def test_recycles_connection_after_3300_seconds(
        self, fake_aurora_module: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        t = {"now": 1000.0}

        def mono() -> float:
            return t["now"]

        monkeypatch.setattr(dsql_connect.time, "monotonic", mono)
        factory = dsql_connect.build_connection_factory("host.dsql.example")
        first = factory()
        first.close = MagicMock()
        t["now"] += dsql_connect.DSQL_CONNECTION_RECYCLE_SECONDS + 1
        second = factory()
        first.close.assert_called_once()
        assert second is not first

    def test_token_not_logged(
        self, fake_aurora_module: Dict[str, Any], caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG)
        secret_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake-token-value"
        with patch.object(
            fake_aurora_module["module"],
            "connect",
            side_effect=lambda **kw: (_ for _ in ()).throw(RuntimeError(secret_token)),
        ):
            with pytest.raises(RuntimeError):
                dsql_connect.connect(user="smc_app", host="h.example")
        for record in caplog.records:
            assert secret_token not in record.getMessage()
