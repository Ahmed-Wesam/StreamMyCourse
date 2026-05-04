from __future__ import annotations

from typing import Protocol


class EnrollmentRepositoryPort(Protocol):
    def has_enrollment(self, *, user_sub: str, course_id: str) -> bool: ...

    def put_enrollment(self, *, user_sub: str, course_id: str, source: str = "self_service") -> None: ...
