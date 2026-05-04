from __future__ import annotations

from services.course_management.contracts import (
    as_course_dto,
    as_course_list,
    as_lesson_dto,
    as_lesson_list,
)


class TestAsCourseDto:
    def test_passes_through_known_status(self) -> None:
        dto = as_course_dto(
            {
                "id": "c1",
                "title": "T",
                "description": "D",
                "status": "PUBLISHED",
                "createdAt": "2026-05-02T00:00:00",
                "updatedAt": "2026-05-02T00:01:00",
            }
        )
        assert dto["id"] == "c1"
        assert dto["title"] == "T"
        assert dto["description"] == "D"
        assert dto["status"] == "PUBLISHED"
        assert dto["createdAt"] == "2026-05-02T00:00:00"
        assert dto["updatedAt"] == "2026-05-02T00:01:00"

    def test_clamps_unknown_status_to_draft(self) -> None:
        dto = as_course_dto({"id": "c1", "title": "T", "description": "", "status": "WEIRD"})
        assert dto["status"] == "DRAFT"

    def test_status_case_sensitive_clamp(self) -> None:
        # Only exact "DRAFT"/"PUBLISHED" pass; any casing variant clamps.
        dto = as_course_dto({"id": "c1", "title": "T", "description": "", "status": "draft"})
        assert dto["status"] == "DRAFT"

    def test_defaults_when_fields_missing(self) -> None:
        dto = as_course_dto({})
        assert dto["id"] == ""
        assert dto["title"] == ""
        assert dto["description"] == ""
        assert dto["status"] == "DRAFT"
        # Timestamps are NotRequired and absent when not provided.
        assert "createdAt" not in dto
        assert "updatedAt" not in dto

    def test_string_coerces_non_string_inputs(self) -> None:
        dto = as_course_dto({"id": 123, "title": None, "description": 0})
        assert dto["id"] == "123"
        # `None` stringifies to "None"; document the existing behavior so a
        # future refactor that swaps the coercion strategy is visible.
        assert dto["title"] == "None"
        assert dto["description"] == "0"

    def test_enrolled_flag(self) -> None:
        dto = as_course_dto(
            {"id": "c1", "title": "T", "description": "", "status": "PUBLISHED", "enrolled": True}
        )
        assert dto["enrolled"] is True


class TestAsLessonDto:
    def test_passes_through_known_video_status(self) -> None:
        dto = as_lesson_dto(
            {
                "id": "l1",
                "title": "Intro",
                "order": 1,
                "videoKey": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/lessons/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/video/11111111-1111-4111-8111-111111111111.mp4",
                "videoStatus": "ready",
                "duration": 42,
            }
        )
        assert dto == {
            "id": "l1",
            "title": "Intro",
            "order": 1,
            "videoStatus": "ready",
            "duration": 42,
        }

    def test_clamps_unknown_video_status_to_pending(self) -> None:
        dto = as_lesson_dto({"id": "l1", "title": "x", "order": 1, "videoStatus": "uploading"})
        assert dto["videoStatus"] == "pending"

    def test_defaults_when_fields_missing(self) -> None:
        dto = as_lesson_dto({})
        assert dto["id"] == ""
        assert dto["title"] == ""
        assert dto["order"] == 0
        assert dto["videoStatus"] == "pending"
        # videoKey is never exposed; duration only when explicitly present.
        assert "videoKey" not in dto
        assert "duration" not in dto

    def test_videokey_present_but_none_is_omitted(self) -> None:
        dto = as_lesson_dto({"id": "l1", "title": "x", "order": 1, "videoKey": None})
        assert "videoKey" not in dto

    def test_order_coerces_to_int(self) -> None:
        dto = as_lesson_dto({"id": "l1", "title": "x", "order": "3"})
        assert dto["order"] == 3
        # Falsy values fall back to 0 via `or 0`.
        dto2 = as_lesson_dto({"id": "l1", "title": "x", "order": None})
        assert dto2["order"] == 0


class TestAsCourseList:
    def test_maps_each_item(self) -> None:
        items = [
            {"id": "c1", "title": "A", "status": "DRAFT"},
            {"id": "c2", "title": "B", "status": "PUBLISHED"},
        ]
        result = as_course_list(items)
        assert [c["id"] for c in result] == ["c1", "c2"]
        assert [c["status"] for c in result] == ["DRAFT", "PUBLISHED"]

    def test_empty(self) -> None:
        assert as_course_list([]) == []


class TestAsLessonList:
    def test_maps_each_item(self) -> None:
        items = [
            {"id": "l1", "title": "A", "order": 1, "videoStatus": "pending"},
            {"id": "l2", "title": "B", "order": 2, "videoStatus": "ready"},
        ]
        result = as_lesson_list(items)
        assert [l["videoStatus"] for l in result] == ["pending", "ready"]

    def test_empty(self) -> None:
        assert as_lesson_list([]) == []
