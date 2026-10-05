"""RS-16: lesson transcript write, markup/length checks, and entitled reads."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Forbidden
from services.course_management.models import Course, Lesson
from services.course_management.service import CourseManagementService

_COURSE = "11111111-1111-4111-8111-111111111111"
_LESSON = "22222222-2222-4222-8222-222222222222"
_TRANSCRIPT_CAP = 20_000


def _lesson(**kwargs: object) -> Lesson:
    defaults = {
        "id": _LESSON,
        "title": "Intro",
        "order": 1,
        "moduleId": "33333333-3333-4333-8333-333333333333",
        "transcript": "Existing notes",
    }
    defaults.update(kwargs)
    return Lesson(**defaults)  # type: ignore[arg-type]


def _course() -> Course:
    return Course(
        id=_COURSE,
        title="T",
        description="D",
        status="PUBLISHED",
        createdBy="owner",
    )


@pytest.fixture
def repo() -> MagicMock:
    mock = MagicMock()
    mock.get_lesson_by_id.return_value = _lesson()
    mock.get_course.return_value = _course()
    return mock


@pytest.fixture
def course_access() -> MagicMock:
    mock = MagicMock()
    mock.has_course_access.return_value = True
    return mock


@pytest.fixture
def service(repo: MagicMock, course_access: MagicMock) -> CourseManagementService:
    return CourseManagementService(repo, None, course_access=course_access)


def test_update_lesson_persists_transcript(
    service: CourseManagementService, repo: MagicMock
) -> None:
    service.update_lesson(_COURSE, _LESSON, "Renamed", transcript="Plain lecture text")
    repo.update_lesson_title.assert_called_once_with(
        course_id=_COURSE, lesson_id=_LESSON, title="Renamed"
    )
    repo.update_lesson_transcript.assert_called_once_with(
        course_id=_COURSE, lesson_id=_LESSON, transcript="Plain lecture text"
    )


def test_update_lesson_without_transcript_leaves_it(
    service: CourseManagementService, repo: MagicMock
) -> None:
    service.update_lesson(_COURSE, _LESSON, "Renamed")
    repo.update_lesson_transcript.assert_not_called()


@pytest.mark.parametrize("bad", ["<script>alert(1)</script>", "Use <b>bold</b> here"])
def test_transcript_rejects_tag_like(
    service: CourseManagementService, repo: MagicMock, bad: str
) -> None:
    with pytest.raises(BadRequest, match="Invalid markup in transcript"):
        service.update_lesson(_COURSE, _LESSON, "Title", transcript=bad)
    repo.update_lesson_transcript.assert_not_called()


def test_transcript_allows_plain_less_than(
    service: CourseManagementService, repo: MagicMock
) -> None:
    text = "Interpret p < 0.05 in the write-up."
    service.update_lesson(_COURSE, _LESSON, "Title", transcript=text)
    assert repo.update_lesson_transcript.call_args.kwargs["transcript"] == text


def test_transcript_over_cap_rejected(
    service: CourseManagementService, repo: MagicMock
) -> None:
    with pytest.raises(BadRequest):
        service.update_lesson(_COURSE, _LESSON, "Title", transcript="a" * (_TRANSCRIPT_CAP + 1))
    repo.update_lesson_transcript.assert_not_called()


def test_transcript_at_cap_accepted(
    service: CourseManagementService, repo: MagicMock
) -> None:
    text = "a" * _TRANSCRIPT_CAP
    service.update_lesson(_COURSE, _LESSON, "Title", transcript=text)
    assert repo.update_lesson_transcript.call_args.kwargs["transcript"] == text


def test_entitled_student_reads_transcript(
    service: CourseManagementService, course_access: MagicMock
) -> None:
    course_access.has_course_access.return_value = True
    body = service.get_lesson_transcript(
        _COURSE, _LESSON, cognito_sub="student-1", role="student"
    )
    assert body["transcript"] == "Existing notes"


def test_other_student_transcript_forbidden(
    service: CourseManagementService, course_access: MagicMock, repo: MagicMock
) -> None:
    course_access.has_course_access.return_value = False
    with pytest.raises(Forbidden):
        service.get_lesson_transcript(
            _COURSE, _LESSON, cognito_sub="other", role="student"
        )
    repo.update_lesson_transcript.assert_not_called()
