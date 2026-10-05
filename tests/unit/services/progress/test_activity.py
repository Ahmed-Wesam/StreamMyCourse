"""RS-16: activity-day writes, streak, and GET /me/activity merge."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from services.progress.ports import ActivityEvent
from services.progress.service import LessonProgressService

_COURSE = "11111111-1111-4111-8111-111111111111"
_LESSON = "22222222-2222-4222-8222-222222222222"
_FIXED = datetime(2026, 10, 4, 15, 30, tzinfo=timezone.utc)


def _clock() -> datetime:
    return _FIXED


class _ActivityRepo:
    def __init__(self) -> None:
        self.days: dict[str, set[date]] = {}
        self.events: list[ActivityEvent] = []
        self.recorded: list[tuple[str, date]] = []

    def record_activity_day(self, *, user_sub: str, day: date) -> None:
        self.recorded.append((user_sub, day))
        self.days.setdefault(user_sub, set()).add(day)

    def list_activity_days(self, *, user_sub: str) -> list[date]:
        return sorted(self.days.get(user_sub, set()))

    def _mine(self, user_sub: str) -> list[ActivityEvent]:
        return [event for event in self.events if event.user_sub == user_sub]

    def list_lesson_completions(self, *, user_sub: str) -> list[ActivityEvent]:
        return [e for e in self._mine(user_sub) if e.kind == "lesson_completion"]

    def list_quiz_attempts(self, *, user_sub: str) -> list[ActivityEvent]:
        return [e for e in self._mine(user_sub) if e.kind == "quiz_attempt"]

    def list_assignment_submissions(self, *, user_sub: str) -> list[ActivityEvent]:
        return [e for e in self._mine(user_sub) if e.kind == "assignment_submission"]

    def list_certificates(self, *, user_sub: str) -> list[ActivityEvent]:
        return [e for e in self._mine(user_sub) if e.kind == "certificate"]


def _event(
    kind: str,
    *,
    user_sub: str,
    at: datetime,
    resource_id: str,
    title: str = "Item",
) -> ActivityEvent:
    return ActivityEvent(
        kind=kind,
        occurred_at=at,
        user_sub=user_sub,
        title=title,
        course_id=_COURSE,
        resource_id=resource_id,
    )


def _service(repo: _ActivityRepo) -> LessonProgressService:
    access = MagicMock()
    access.has_course_access.return_value = True
    course_repo = MagicMock()
    course_repo.get_lesson_by_id.return_value = MagicMock(id=_LESSON, moduleId="m1")
    progress = MagicMock()
    progress.upsert_progress.return_value = MagicMock(
        lesson_id=_LESSON,
        completed=False,
        last_position_sec=1,
        completed_at=None,
    )
    # The activity repo is the progress repo for these tests.
    return LessonProgressService(
        progress,  # type: ignore[arg-type]
        access,
        course_repo,
        clock=_clock,
    )


def test_progress_upsert_records_utc_day(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _ActivityRepo()
    access = MagicMock()
    access.has_course_access.return_value = True
    course_repo = MagicMock()
    course_repo.get_lesson_by_id.return_value = MagicMock(id=_LESSON, moduleId="m1")
    progress = MagicMock()
    progress.upsert_progress.return_value = MagicMock(
        lesson_id=_LESSON,
        completed=True,
        last_position_sec=10,
        completed_at=_FIXED,
    )
    progress.record_activity_day.side_effect = repo.record_activity_day
    svc = LessonProgressService(
        progress,
        access,
        course_repo,
        clock=_clock,
    )
    svc.update_lesson_progress(
        user_sub="user-a",
        course_id=_COURSE,
        lesson_id=_LESSON,
        position=10,
        duration=10,
        mark_complete=True,
        role="student",
    )
    progress.record_activity_day.assert_called_once_with(user_sub="user-a", day=date(2026, 10, 4))


def test_failed_upsert_does_not_record_day() -> None:
    access = MagicMock()
    access.has_course_access.return_value = True
    course_repo = MagicMock()
    course_repo.get_lesson_by_id.return_value = MagicMock(id=_LESSON, moduleId="m1")
    progress = MagicMock()
    progress.upsert_progress.side_effect = RuntimeError("db down")
    svc = LessonProgressService(progress, access, course_repo, clock=_clock)
    with pytest.raises(RuntimeError):
        svc.update_lesson_progress(
            user_sub="user-a",
            course_id=_COURSE,
            lesson_id=_LESSON,
            position=1,
            duration=10,
            role="student",
        )
    progress.record_activity_day.assert_not_called()


def _activity_service(repo: _ActivityRepo) -> LessonProgressService:
    access = MagicMock()
    course_repo = MagicMock()
    return LessonProgressService(repo, access, course_repo, clock=_clock)  # type: ignore[arg-type]


def test_streak_counts_consecutive_days_through_today() -> None:
    repo = _ActivityRepo()
    today = date(2026, 10, 4)
    repo.days["user-a"] = {today, today - timedelta(days=1), today - timedelta(days=2)}
    body = _activity_service(repo).get_my_activity(user_sub="user-a")
    assert body["streakDays"] == 3


def test_streak_keeps_yesterday_when_today_is_empty() -> None:
    repo = _ActivityRepo()
    today = date(2026, 10, 4)
    repo.days["user-a"] = {today - timedelta(days=1), today - timedelta(days=2)}
    body = _activity_service(repo).get_my_activity(user_sub="user-a")
    assert body["streakDays"] == 2


def test_streak_breaks_on_gap_and_ignores_old_run() -> None:
    repo = _ActivityRepo()
    today = date(2026, 10, 4)
    repo.days["user-a"] = {today, today - timedelta(days=2)}
    body = _activity_service(repo).get_my_activity(user_sub="user-a")
    assert body["streakDays"] == 1


def test_merge_order_newest_first_and_limit_20() -> None:
    repo = _ActivityRepo()
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    kinds = (
        "lesson_completion",
        "quiz_attempt",
        "assignment_submission",
        "certificate",
    )
    for i in range(25):
        repo.events.append(
            _event(
                kinds[i % 4],
                user_sub="user-a",
                at=base + timedelta(hours=i),
                resource_id=f"r{i:02d}",
                title=f"T{i}",
            )
        )
    body = _activity_service(repo).get_my_activity(user_sub="user-a")
    items = body["items"]
    assert len(items) == 20
    stamps = [item["at"] for item in items]
    assert stamps == sorted(stamps, reverse=True)
    assert items[0]["resourceId"] == "r24"
    assert {item["kind"] for item in items} <= set(kinds)


def test_user_a_does_not_see_user_b() -> None:
    repo = _ActivityRepo()
    when = datetime(2026, 10, 4, 12, tzinfo=timezone.utc)
    repo.events.append(_event("lesson_completion", user_sub="user-a", at=when, resource_id="a1", title="Mine"))
    repo.events.append(
        _event("certificate", user_sub="user-b", at=when + timedelta(minutes=1), resource_id="b1", title="Theirs")
    )
    repo.days["user-b"] = {date(2026, 10, 4), date(2026, 10, 3), date(2026, 10, 2)}
    body = _activity_service(repo).get_my_activity(user_sub="user-a")
    assert [item["resourceId"] for item in body["items"]] == ["a1"]
    assert body["streakDays"] == 0


def test_get_me_activity_uses_jwt_subject_only() -> None:
    from services.progress.controller import handle_progress_request

    svc = MagicMock()
    svc.get_my_activity.return_value = {"streakDays": 0, "items": []}
    event: dict[str, Any] = {
        "requestContext": {
            "http": {"method": "GET", "path": "/me/activity"},
            "authorizer": {"claims": {"sub": "user-a", "custom:role": "student"}},
        },
        "rawPath": "/me/activity",
        "body": json.dumps({"userSub": "user-b"}),
    }
    resp = handle_progress_request(event, origin="https://example.com", progress_svc=svc)
    assert resp["statusCode"] == 200
    svc.get_my_activity.assert_called_once_with(user_sub="user-a")
    assert "user-b" not in resp["body"]
