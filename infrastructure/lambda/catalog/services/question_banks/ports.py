"""Ports for question bank domain services."""

from __future__ import annotations

from typing import Protocol


class CourseMutateAuthorizerPort(Protocol):
    def ensure_course_mutable_by_actor(
        self, course_id: str, *, cognito_sub: str, role: str
    ) -> None: ...

    def ensure_course_publisher_read_scope(
        self, course_id: str, *, cognito_sub: str, role: str
    ) -> None: ...


class StudentLessonAccessPort(Protocol):
    def viewer_has_lesson_access(
        self, course_id: str, cognito_sub: str, role: str
    ) -> bool: ...


class CourseReadPort(Protocol):
    def get_course_status(self, course_id: str) -> str | None: ...
