"""Ports for question bank domain services."""

from __future__ import annotations

from typing import Protocol


class CourseMutateAuthorizerPort(Protocol):
    def ensure_course_mutable_by_actor(
        self, course_id: str, *, cognito_sub: str, role: str
    ) -> None: ...
