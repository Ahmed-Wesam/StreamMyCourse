"""Factory helpers that create courses/lessons via the API and register them
for cleanup with the test's request finalizer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, List

from helpers.api import ApiClient

# Prefix used on every test-created title so the session-end safety net can
# identify leftovers regardless of which test produced them.
TEST_TITLE_PREFIX = "integ-test-"


def make_test_title(label: str = "course") -> str:
    return f"{TEST_TITLE_PREFIX}{label}-{uuid.uuid4()}"


@dataclass
class CourseHandle:
    course_id: str
    title: str


@dataclass
class LessonHandle:
    course_id: str
    lesson_id: str
    title: str
    order: int


def build_course_factory(
    api: ApiClient,
    register_course_for_cleanup: Callable[[str], None],
) -> Callable[..., CourseHandle]:
    """Returns a callable that creates a course via POST /courses and registers
    its id for cleanup via DELETE /courses/{id} in the caller's finalizer."""

    def make_course(*, label: str = "course", description: str = "") -> CourseHandle:
        title = make_test_title(label)
        resp = api.create_course(title=title, description=description)
        assert resp.status_code == 201, f"create_course failed: {resp.status_code} {resp.text}"
        body = resp.json()
        course_id = str(body["id"])
        register_course_for_cleanup(course_id)
        return CourseHandle(course_id=course_id, title=title)

    return make_course


def build_lesson_factory(
    api: ApiClient,
) -> Callable[..., LessonHandle]:
    """Returns a callable that creates a lesson under a given course. Lesson
    cleanup is implicit because deleting the course cascades to its lessons,
    so we don't need a separate finalizer registration here."""

    def make_lesson(course_id: str, *, label: str = "lesson") -> LessonHandle:
        title = make_test_title(label)
        resp = api.create_lesson(course_id, title=title)
        assert resp.status_code == 201, f"create_lesson failed: {resp.status_code} {resp.text}"
        body = resp.json()
        return LessonHandle(
            course_id=course_id,
            lesson_id=str(body["lessonId"]),
            title=title,
            order=int(body["order"]),
        )

    return make_lesson


def collect_test_course_ids_from_list(items: List[dict]) -> List[str]:
    """Filter a /courses list response down to test-created courses by title
    prefix. Used by the session-end safety net to be conservative."""
    return [
        str(item["id"])
        for item in items
        if str(item.get("title", "")).startswith(TEST_TITLE_PREFIX)
    ]
