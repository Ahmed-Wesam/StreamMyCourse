"""DSQL-2 S4: UserDeletionService registry semantics."""

from __future__ import annotations

import pytest

from services.user_deletion.errors import UserDeletionBlocked
from services.user_deletion.identity import register_identity_steps
from services.user_deletion.registry import UserDeletionRegistry
from services.user_deletion.service import UserDeletionService


class _FakeDeleter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def delete_user_row(self, user_sub: str) -> int:
        self.calls.append(user_sub)
        return 1


class TestUserDeletionService:
    def test_steps_run_ascending_order(self) -> None:
        registry = UserDeletionRegistry()
        order_log: list[str] = []
        registry.register(name="child", order=100, run=lambda s: order_log.append("child"))
        register_identity_steps(registry, _FakeDeleter())
        svc = UserDeletionService(registry)
        svc.delete_user("sub-1")
        assert order_log == ["child"]

    def test_empty_user_sub_raises(self) -> None:
        registry = UserDeletionRegistry()
        register_identity_steps(registry, _FakeDeleter())
        svc = UserDeletionService(registry)
        with pytest.raises(ValueError, match="user_sub"):
            svc.delete_user("")
        assert _FakeDeleter().calls == []

    def test_23503_becomes_blocked_and_stops(self) -> None:
        registry = UserDeletionRegistry()

        def fail_fk(user_sub: str) -> None:
            err = Exception("fk")
            err.pgcode = "23503"  # type: ignore[attr-defined]
            raise err

        registry.register(name="purchases", order=200, run=fail_fk)
        register_identity_steps(registry, _FakeDeleter())
        svc = UserDeletionService(registry)
        with pytest.raises(UserDeletionBlocked) as exc_info:
            svc.delete_user("sub-1")
        assert exc_info.value.step_name == "purchases"

    def test_second_delete_after_zero_rows_succeeds(self) -> None:
        deleter = _FakeDeleter()
        deleter.delete_user_row = lambda user_sub: 0  # type: ignore[method-assign]
        registry = UserDeletionRegistry()
        register_identity_steps(registry, deleter)
        svc = UserDeletionService(registry)
        svc.delete_user("sub-1")
        svc.delete_user("sub-1")

    def test_register_identity_steps_single_users_step(self) -> None:
        registry = UserDeletionRegistry()
        register_identity_steps(registry, _FakeDeleter())
        steps = registry.ordered_steps()
        assert len(steps) == 1
        assert steps[0].name == "users"
        assert steps[0].order == 1000
