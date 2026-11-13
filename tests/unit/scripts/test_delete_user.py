"""DSQL-2 S5: scripts/delete-user.py (injected boundaries)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_MODULE_PATH = _ROOT / "scripts" / "delete-user.py"


def _load():
    spec = importlib.util.spec_from_file_location("delete_user", _MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeCognito:
    def __init__(self) -> None:
        self.disabled: list[str] = []
        self.deleted: list[str] = []
        self.username: Optional[str] = "email-user"

    def resolve_username(self, *, user_pool_id: str, user_sub: str) -> Optional[str]:
        return self.username

    def disable_user(self, *, user_pool_id: str, username: str) -> None:
        self.disabled.append(username)

    def delete_user(self, *, user_pool_id: str, username: str) -> None:
        self.deleted.append(username)


class FakeService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def delete_user(self, user_sub: str) -> None:
        self.calls.append(user_sub)


class TestDeleteUserScript:
    def test_dry_run_no_calls(self) -> None:
        mod = _load()
        cognito = FakeCognito()
        svc = FakeService()

        code = mod.run(
            ["--user-sub", "abc-def-123"],
            cognito=cognito,
            service_factory=lambda _e: svc,
            endpoint_resolver=lambda: "host.dsql.example",
            pool_resolver=lambda: "pool-id",
        )
        assert code == 0
        assert cognito.disabled == []
        assert svc.calls == []

    def test_execute_order(self) -> None:
        mod = _load()
        cognito = FakeCognito()
        order: list[str] = []
        svc = FakeService()
        svc.delete_user = lambda s: order.append("db")  # type: ignore[method-assign]

        def disable(**_kw: object) -> None:
            order.append("disable")

        def delete(**_kw: object) -> None:
            order.append("cognito_delete")

        cognito.disable_user = disable  # type: ignore[method-assign]
        cognito.delete_user = delete  # type: ignore[method-assign]

        code = mod.run(
            ["--user-sub", "abc-def-123", "--execute"],
            cognito=cognito,
            service_factory=lambda _e: svc,
            endpoint_resolver=lambda: "host.dsql.example",
            pool_resolver=lambda: "pool-id",
        )
        assert code == 0
        assert order == ["disable", "db", "cognito_delete", "db"]

    def test_blocked_exit_2_no_cognito_delete(self) -> None:
        mod = _load()
        from services.user_deletion.errors import UserDeletionBlocked

        cognito = FakeCognito()
        order: list[str] = []

        class BlockedService:
            def delete_user(self, user_sub: str) -> None:
                order.append("db")
                raise UserDeletionBlocked("users")

        cognito.delete_user = lambda **_kw: order.append("cognito_delete")  # type: ignore[method-assign]

        code = mod.run(
            ["--user-sub", "abc-def-123", "--execute"],
            cognito=cognito,
            service_factory=lambda _e: BlockedService(),
            endpoint_resolver=lambda: "host.dsql.example",
            pool_resolver=lambda: "pool-id",
        )
        assert code == 2
        assert order == ["db"]
        assert cognito.deleted == []

    def test_user_not_found_on_delete_still_ok(self) -> None:
        mod = _load()
        cognito = FakeCognito()
        cognito.delete_user = lambda **_kw: None  # type: ignore[method-assign]
        code = mod.run(
            ["--user-sub", "abc-def-123", "--execute"],
            cognito=cognito,
            service_factory=lambda _e: FakeService(),
            endpoint_resolver=lambda: "host.dsql.example",
            pool_resolver=lambda: "pool-id",
        )
        assert code == 0

    def test_empty_endpoint_nonzero(self) -> None:
        mod = _load()
        code = mod.run(
            ["--user-sub", "abc-def-123", "--execute"],
            cognito=FakeCognito(),
            service_factory=lambda _e: FakeService(),
            endpoint_resolver=lambda: "",
            pool_resolver=lambda: "pool-id",
        )
        assert code != 0
        assert FakeCognito().disabled == []

    def test_invalid_user_sub_rejects_filter(self) -> None:
        mod = _load()
        cognito = FakeCognito()
        called = {"resolve": False}

        def resolve(**_kw: object) -> None:
            called["resolve"] = True
            return None

        cognito.resolve_username = resolve  # type: ignore[method-assign]
        code = mod.run(
            ["--user-sub", "bad sub", "--execute"],
            cognito=cognito,
            service_factory=lambda _e: FakeService(),
            endpoint_resolver=lambda: "host.dsql.example",
            pool_resolver=lambda: "pool-id",
        )
        assert code != 0
        assert called["resolve"] is False

