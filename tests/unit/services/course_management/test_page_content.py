"""RS-7 Slice A: course page_content validation, update, and DTO mapping."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Forbidden
from services.course_management.contracts import as_course_dto, as_course_list
from services.course_management.course_page_validation import validate_and_normalize_course_page
from services.course_management.models import Course
from services.course_management.service import CourseManagementService

_VID = "11111111-1111-4111-8111-111111111111"


def _course(**kwargs: object) -> Course:
    defaults = {
        "id": _VID,
        "title": "T",
        "description": "D",
        "status": "PUBLISHED",
        "createdBy": "owner-sub",
    }
    defaults.update(kwargs)
    return Course(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(repo: MagicMock) -> CourseManagementService:
    return CourseManagementService(repo, None, course_access=MagicMock())


class TestValidateCoursePageMarkup:
    def test_p_less_than_in_lead_is_stored(self) -> None:
        page = validate_and_normalize_course_page(
            {
                "outcomes": {
                    "lead": "Interpret significance including p < 0.05 in your write-up.",
                }
            }
        )
        assert page["outcomes"]["lead"] == (
            "Interpret significance including p < 0.05 in your write-up."
        )

    @pytest.mark.parametrize("bad", ["<script>alert(1)</script>", "Use <b>bold</b> here"])
    def test_tag_like_markup_rejected(self, bad: str) -> None:
        with pytest.raises(BadRequest):
            validate_and_normalize_course_page({"curriculumLead": bad})


class TestValidateCoursePageFieldCaps:
    def test_subtitle_allows_long_hero_copy(self) -> None:
        text = "a" * 400
        page = validate_and_normalize_course_page({"subtitle": text})
        assert page["subtitle"] == text

    def test_level_over_40_characters_rejected(self) -> None:
        with pytest.raises(BadRequest):
            validate_and_normalize_course_page({"level": "x" * 41})


class TestValidateCoursePageTypes:
    @pytest.mark.parametrize("bad_hours", [True, 0, 201])
    def test_estimated_hours_invalid(self, bad_hours: object) -> None:
        with pytest.raises(BadRequest):
            validate_and_normalize_course_page({"estimatedHours": bad_hours})

    def test_non_object_page_rejected(self) -> None:
        with pytest.raises(BadRequest):
            validate_and_normalize_course_page([])  # type: ignore[arg-type]

    def test_unknown_top_level_key_rejected(self) -> None:
        with pytest.raises(BadRequest):
            validate_and_normalize_course_page({"notAField": "x"})

    def test_unknown_key_in_section_rejected(self) -> None:
        with pytest.raises(BadRequest):
            validate_and_normalize_course_page({"problem": {"extra": "nope"}})


class TestUpdateCoursePagePersistence:
    def test_update_without_page_key_leaves_page_unchanged(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        service.update_course(_VID, "T2", "D2")
        repo.update_course.assert_called_once_with(
            course_id=_VID, title="T2", description="D2"
        )

    def test_update_with_page_rejected(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        page = {"subtitle": "Sub", "level": "Intermediate", "estimatedHours": 12}
        with pytest.raises(BadRequest):
            service.update_course(_VID, "T2", "D2", page=page)
        repo.update_course.assert_not_called()

    def test_update_with_empty_page_rejected(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        with pytest.raises(BadRequest):
            service.update_course(_VID, "T", "D", page={})
        repo.update_course.assert_not_called()

    def test_invalid_page_does_not_call_repo(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        with pytest.raises(BadRequest):
            service.update_course(_VID, "T", "D", page={"estimatedHours": True})
        repo.update_course.assert_not_called()


class TestCoursePageDtoMapping:
    def _base_row(self, page: dict) -> dict:
        return {
            "id": _VID,
            "title": "T",
            "description": "D",
            "status": "PUBLISHED",
            "pageContent": page,
        }

    def test_list_includes_card_fields_not_problem(self) -> None:
        page = {
            "level": "Advanced",
            "estimatedHours": 40,
            "subtitle": "Short",
            "problem": {"items": ["Pain point"]},
        }
        dto = as_course_list([self._base_row(page)])[0]
        assert dto["level"] == "Advanced"
        assert dto["estimatedHours"] == 40
        assert dto["subtitle"] == "Short"
        assert "problem" not in dto

    def test_detail_includes_problem_when_filled_omits_empty_outcomes(self) -> None:
        page = {
            "problem": {"items": ["Stat confusion"]},
            "outcomes": {"heading": " ", "lead": "", "items": []},
        }
        dto = as_course_dto(self._base_row(page), detail=True)
        assert dto["problem"]["items"] == ["Stat confusion"]
        assert "outcomes" not in dto

    def test_detail_dto_tolerates_corrupt_stored_section(self) -> None:
        page = {"outcomes": {"items": 123}, "level": "Beginner"}
        dto = as_course_dto(self._base_row(page), detail=True)
        assert dto["level"] == "Beginner"
        assert "outcomes" not in dto


class TestNonOwnerPageUpdate:
    def test_non_owner_cannot_modify_before_page_write(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(createdBy="owner-sub")
        with pytest.raises(Forbidden):
            service.ensure_can_modify_course(
                _VID, cognito_sub="other-sub", role="teacher"
            )
        repo.update_course.assert_not_called()


class TestNormalizedPageSizeCap:
    def test_page_over_16kb_rejected(self) -> None:
        items = ["a" * 160 for _ in range(120)]
        with pytest.raises(BadRequest):
            validate_and_normalize_course_page({"catalogSkills": items})


class TestValidateDropsEmptyStrings:
    def test_empty_catalog_skills_stripped(self) -> None:
        page = validate_and_normalize_course_page(
            {"catalogSkills": ["  ", "Real skill", ""]}
        )
        assert page["catalogSkills"] == ["Real skill"]
