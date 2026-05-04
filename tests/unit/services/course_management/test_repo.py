"""Unit tests for `services.course_management.repo`.

These tests run **without boto3 installed**: the module-level `boto3`, `Attr`,
and `Key` bindings are replaced with `MagicMock`s, so condition-builder calls
become harmless mock chains and the constructor's `boto3.resource('dynamodb')
.Table(...)` chain returns a mock too. We then replace `repo._table` with a
fresh mock to get clean call assertions.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import services.course_management.repo as repo_mod
from services.course_management.models import Course, Lesson


@pytest.fixture
def repo_with_table(monkeypatch: pytest.MonkeyPatch):
    """Construct a `CourseCatalogRepository` with the boto3 boundary mocked out."""
    monkeypatch.setattr(repo_mod, "boto3", MagicMock())
    monkeypatch.setattr(repo_mod, "Attr", MagicMock())
    monkeypatch.setattr(repo_mod, "Key", MagicMock())

    repo = repo_mod.CourseCatalogRepository("test-table")
    mock_table = MagicMock()
    repo._table = mock_table  # noqa: SLF001 — test-only override.
    return repo, mock_table


# --- Constructor edge cases ----------------------------------------------------


class TestRepositoryInit:
    def test_empty_table_name_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(repo_mod, "boto3", MagicMock())
        with pytest.raises(RuntimeError, match="TABLE_NAME"):
            repo_mod.CourseCatalogRepository("")

    def test_missing_boto3_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(repo_mod, "boto3", None)
        with pytest.raises(RuntimeError, match="boto3 is not available"):
            repo_mod.CourseCatalogRepository("test-table")


# --- Pure formatters -----------------------------------------------------------


class TestFormatCourse:
    def test_extracts_id_from_pk(self) -> None:
        course = repo_mod.CourseCatalogRepository._format_course(
            {
                "PK": "COURSE#abc",
                "title": "Hello",
                "description": "World",
                "status": "PUBLISHED",
                "createdAt": "2026-05-02",
                "updatedAt": "2026-05-02",
            }
        )
        assert course == Course(
            id="abc",
            title="Hello",
            description="World",
            status="PUBLISHED",
            createdAt="2026-05-02",
            updatedAt="2026-05-02",
        )

    def test_missing_fields_default_safely(self) -> None:
        course = repo_mod.CourseCatalogRepository._format_course({})
        assert course.id == ""
        assert course.title == ""
        assert course.description == ""
        # Status defaults to DRAFT, never None.
        assert course.status == "DRAFT"

    def test_none_values_coerce_to_safe_defaults(self) -> None:
        course = repo_mod.CourseCatalogRepository._format_course(
            {"PK": "COURSE#abc", "title": None, "status": None}
        )
        assert course.title == ""
        assert course.status == "DRAFT"


class TestFormatLesson:
    def test_modern_path_uses_explicit_order_attribute(self) -> None:
        lesson = repo_mod.CourseCatalogRepository._format_lesson(
            {
                "SK": "LESSON#9d6c2a1e-uuid",
                "lessonId": "9d6c2a1e-uuid",
                "title": "Intro",
                "order": 5,
                "videoKey": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/lessons/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/video/11111111-1111-4111-8111-111111111111.mp4",
                "videoStatus": "ready",
                "duration": 12,
            }
        )
        assert lesson == Lesson(
            id="9d6c2a1e-uuid",
            title="Intro",
            order=5,
            videoKey="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/lessons/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/video/11111111-1111-4111-8111-111111111111.mp4",
            videoStatus="ready",
            duration=12,
            thumbnailKey="",
        )

    def test_legacy_path_parses_order_from_numeric_sk(self) -> None:
        # Pre-migration row: no `order` attribute, SK encodes the order as
        # `LESSON#003`. Renderer must still produce a usable Lesson.
        lesson = repo_mod.CourseCatalogRepository._format_lesson(
            {"SK": "LESSON#003", "lessonId": "legacy", "title": "Old"}
        )
        assert lesson.order == 3
        assert lesson.id == "legacy"

    def test_legacy_path_falls_back_to_zero_when_sk_not_numeric(self) -> None:
        lesson = repo_mod.CourseCatalogRepository._format_lesson(
            {"SK": "LESSON#abc", "lessonId": "x", "title": "y"}
        )
        assert lesson.order == 0

    def test_defaults_when_fields_missing(self) -> None:
        lesson = repo_mod.CourseCatalogRepository._format_lesson({})
        assert lesson.id == ""
        assert lesson.title == ""
        assert lesson.order == 0
        assert lesson.videoKey == ""
        assert lesson.videoStatus == "pending"
        assert lesson.duration == 0
        assert lesson.thumbnailKey == ""


# --- Query / read helpers ------------------------------------------------------


class TestListCourses:
    def test_returns_formatted_courses(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.scan.return_value = {
            "Items": [
                {"PK": "COURSE#a", "title": "A", "status": "DRAFT"},
                {"PK": "COURSE#b", "title": "B", "status": "PUBLISHED"},
            ]
        }
        result = repo.list_courses()
        assert [c.id for c in result] == ["a", "b"]
        assert [c.status for c in result] == ["DRAFT", "PUBLISHED"]

    def test_missing_items_returns_empty(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.scan.return_value = {}
        assert repo.list_courses() == []


class TestListCoursesByInstructor:
    def test_filters_and_sorts_by_created_at(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.scan.return_value = {
            "Items": [
                {
                    "PK": "COURSE#b",
                    "SK": "METADATA",
                    "title": "B",
                    "createdBy": "teacher-1",
                    "createdAt": "2026-05-02T00:00:00+00:00",
                },
                {
                    "PK": "COURSE#a",
                    "SK": "METADATA",
                    "title": "A",
                    "createdBy": "teacher-1",
                    "createdAt": "2026-05-01T00:00:00+00:00",
                },
            ]
        }
        out = repo.list_courses_by_instructor("teacher-1")
        assert [c.id for c in out] == ["a", "b"]
        fe = table.scan.call_args.kwargs.get("FilterExpression")
        assert fe is not None

    def test_blank_instructor_returns_empty(self, repo_with_table) -> None:
        repo, table = repo_with_table
        assert repo.list_courses_by_instructor("") == []
        assert repo.list_courses_by_instructor("   ") == []
        table.scan.assert_not_called()


class TestGetCourse:
    def test_present_course_is_formatted(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.get_item.return_value = {
            "Item": {"PK": "COURSE#abc", "title": "X", "status": "DRAFT"}
        }
        course = repo.get_course("abc")
        assert course is not None and course.id == "abc"
        # The Key passed must use the `COURSE#` PK and `METADATA` SK.
        kwargs = table.get_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "COURSE#abc", "SK": "METADATA"}

    def test_missing_course_returns_none(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.get_item.return_value = {}
        assert repo.get_course("missing") is None


class TestListLessons:
    def test_sorts_unsorted_items_by_order(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.query.return_value = {
            "Items": [
                {"SK": "LESSON#x", "lessonId": "x", "title": "X", "order": 3},
                {"SK": "LESSON#y", "lessonId": "y", "title": "Y", "order": 1},
                {"SK": "LESSON#z", "lessonId": "z", "title": "Z", "order": 2},
            ]
        }
        lessons = repo.list_lessons("course1")
        assert [l.order for l in lessons] == [1, 2, 3]
        assert [l.id for l in lessons] == ["y", "z", "x"]

    def test_empty_query_response(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.query.return_value = {}
        assert repo.list_lessons("course1") == []


class TestGetLessonById:
    def test_uses_lesson_sk_with_uuid(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.get_item.return_value = {
            "Item": {
                "lessonId": "lid-abc",
                "title": "L",
                "order": 1,
                "SK": "LESSON#lid-abc",
            }
        }

        lesson = repo.get_lesson_by_id("course1", "lid-abc")

        assert lesson is not None and lesson.id == "lid-abc"
        kwargs = table.get_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "COURSE#course1", "SK": "LESSON#lid-abc"}

    def test_missing_returns_none(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.get_item.return_value = {"Item": None}
        assert repo.get_lesson_by_id("c", "l") is None


# --- Mutators ------------------------------------------------------------------


class TestCreateCourse:
    def test_writes_metadata_item_with_draft_status(
        self, repo_with_table, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo, table = repo_with_table

        # Pin uuid + timestamp for stable assertions.
        monkeypatch.setattr(repo_mod, "uuid4", lambda: "fixed-uuid")
        monkeypatch.setattr(repo_mod, "_now_iso", lambda: "2026-05-02T00:00:00")

        course = repo.create_course("My Course", "Desc")

        assert course.id == "fixed-uuid"
        assert course.status == "DRAFT"
        item = table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "COURSE#fixed-uuid"
        assert item["SK"] == "METADATA"
        assert item["title"] == "My Course"
        assert item["description"] == "Desc"
        assert item["status"] == "DRAFT"
        assert item["createdAt"] == "2026-05-02T00:00:00"
        assert item["updatedAt"] == "2026-05-02T00:00:00"


class TestCreateLesson:
    def test_first_lesson_gets_order_one(
        self, repo_with_table, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo, table = repo_with_table
        table.query.return_value = {"Items": []}
        monkeypatch.setattr(repo_mod, "uuid4", lambda: "lid-1")

        lesson = repo.create_lesson("course1", "First")

        assert lesson.order == 1
        assert lesson.id == "lid-1"
        item = table.put_item.call_args.kwargs["Item"]
        assert item["SK"] == "LESSON#lid-1"
        assert item["order"] == 1
        assert item["videoStatus"] == "pending"
        assert item["videoKey"] == ""

    def test_max_order_plus_one_with_orders_one_and_two(
        self, repo_with_table, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Regression pin for the lesson SK refactor: when there are two
        # existing lessons, next_order MUST come from `max(orders)+1`, not
        # `len(existing)+1`. Both yield 3 here, so add the next test for the
        # case where they diverge.
        repo, table = repo_with_table
        table.query.return_value = {
            "Items": [
                {"SK": "LESSON#a", "lessonId": "a", "order": 1, "title": "A"},
                {"SK": "LESSON#b", "lessonId": "b", "order": 2, "title": "B"},
            ]
        }
        monkeypatch.setattr(repo_mod, "uuid4", lambda: "lid-new")

        lesson = repo.create_lesson("course1", "Third")

        assert lesson.order == 3

    def test_max_order_plus_one_with_orders_one_and_three(
        self, repo_with_table, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The smoking-gun regression: two lessons but with a gap. Old buggy
        # code used `len+1` → 3, which would silently overwrite `b`'s row.
        # The fix uses `max+1` → 4.
        repo, table = repo_with_table
        table.query.return_value = {
            "Items": [
                {"SK": "LESSON#a", "lessonId": "a", "order": 1, "title": "A"},
                {"SK": "LESSON#b", "lessonId": "b", "order": 3, "title": "B"},
            ]
        }
        monkeypatch.setattr(repo_mod, "uuid4", lambda: "lid-new")

        lesson = repo.create_lesson("course1", "Next")

        assert lesson.order == 4, (
            "create_lesson must use max(order)+1, not len(existing)+1"
        )
        item = table.put_item.call_args.kwargs["Item"]
        assert item["order"] == 4


class TestUpdateCourse:
    def test_writes_title_description_and_timestamp(
        self, repo_with_table, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo, table = repo_with_table
        monkeypatch.setattr(repo_mod, "_now_iso", lambda: "2026-05-02T00:00:00")

        repo.update_course("course1", "New Title", "New Desc")

        kwargs = table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "COURSE#course1", "SK": "METADATA"}
        assert kwargs["ExpressionAttributeValues"] == {
            ":t": "New Title",
            ":d": "New Desc",
            ":u": "2026-05-02T00:00:00",
        }


class TestUpdateLessonTitle:
    def test_keys_by_lesson_id(self, repo_with_table) -> None:
        repo, table = repo_with_table
        repo.update_lesson_title("course1", "lid-x", "New title")
        kwargs = table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "COURSE#course1", "SK": "LESSON#lid-x"}
        assert kwargs["ExpressionAttributeValues"] == {":t": "New title"}


class TestSetLessonVideo:
    def test_sets_key_and_status(self, repo_with_table) -> None:
        repo, table = repo_with_table
        repo.set_lesson_video(
            "course1",
            "lid-x",
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/lessons/lid-x/video/11111111-1111-4111-8111-111111111111.mp4",
            "pending",
        )
        kwargs = table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "COURSE#course1", "SK": "LESSON#lid-x"}
        assert kwargs["ExpressionAttributeValues"] == {
            ":k": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/lessons/lid-x/video/11111111-1111-4111-8111-111111111111.mp4",
            ":s": "pending",
        }


class TestSetLessonVideoStatus:
    def test_sets_status_only(self, repo_with_table) -> None:
        repo, table = repo_with_table
        repo.set_lesson_video_status("course1", "lid-x", "ready")
        kwargs = table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "COURSE#course1", "SK": "LESSON#lid-x"}
        assert kwargs["ExpressionAttributeValues"] == {":s": "ready"}


class TestSetCourseStatus:
    def test_aliases_status_reserved_word(self, repo_with_table) -> None:
        repo, table = repo_with_table
        repo.set_course_status("course1", "PUBLISHED")
        kwargs = table.update_item.call_args.kwargs
        assert kwargs["ExpressionAttributeNames"] == {"#course_status": "status"}
        assert kwargs["ExpressionAttributeValues"][":s"] == "PUBLISHED"


# --- Bulk + delete -------------------------------------------------------------


class TestDeleteCourseAndLessons:
    def test_batches_metadata_and_each_lesson(self, repo_with_table) -> None:
        repo, table = repo_with_table
        table.query.return_value = {
            "Items": [
                {"SK": "LESSON#a", "lessonId": "a", "order": 1, "title": "A"},
                {"SK": "LESSON#b", "lessonId": "b", "order": 2, "title": "B"},
            ]
        }
        # Wire up the context manager so `with table.batch_writer() as batch:` works.
        mock_batch = MagicMock()
        table.batch_writer.return_value.__enter__.return_value = mock_batch

        repo.delete_course_and_lessons("course1")

        delete_calls = mock_batch.delete_item.call_args_list
        keys = [c.kwargs["Key"] for c in delete_calls]
        assert {"PK": "COURSE#course1", "SK": "METADATA"} in keys
        assert {"PK": "COURSE#course1", "SK": "LESSON#a"} in keys
        assert {"PK": "COURSE#course1", "SK": "LESSON#b"} in keys
        assert len(delete_calls) == 3


class TestSetLessonOrders:
    def test_each_lesson_gets_an_aliased_update_with_pk_exists_condition(
        self, repo_with_table
    ) -> None:
        repo, table = repo_with_table

        repo.set_lesson_orders("course1", {"l1": 1, "l2": 2, "l3": 3})

        assert table.update_item.call_count == 3
        calls = table.update_item.call_args_list

        seen = {}
        for call in calls:
            kwargs = call.kwargs
            # Reserved word `order` must be aliased.
            assert kwargs["ExpressionAttributeNames"] == {"#order": "order"}
            assert kwargs["UpdateExpression"] == "SET #order = :o"
            # Each per-row update must guard with `Attr('PK').exists()` so a
            # deleted row doesn't get resurrected by the renumber.
            assert "ConditionExpression" in kwargs
            sk = kwargs["Key"]["SK"]
            assert sk.startswith("LESSON#")
            seen[sk.replace("LESSON#", "")] = kwargs["ExpressionAttributeValues"][":o"]

        assert seen == {"l1": 1, "l2": 2, "l3": 3}

    def test_empty_mapping_is_a_noop(self, repo_with_table) -> None:
        repo, table = repo_with_table
        repo.set_lesson_orders("course1", {})
        table.update_item.assert_not_called()


class TestDeleteLesson:
    def test_keys_by_lesson_sk(self, repo_with_table) -> None:
        repo, table = repo_with_table
        repo.delete_lesson("course1", "lid-x")
        kwargs = table.delete_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "COURSE#course1", "SK": "LESSON#lid-x"}
