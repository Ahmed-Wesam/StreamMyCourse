"""RS-14 validation: caps, enums, acknowledgement."""

from __future__ import annotations

import pytest

from services.common.errors import BadRequest
from services.research_team.ports import RequiredCourseRow
from tests.unit.services.research_team.helpers import (
    _COURSE_A,
    _STUDENT,
    make_service,
    valid_submit_body,
)


def _eligible_svc():
    parts = make_service()
    svc, repo, certs, *_ = parts
    repo.required[_COURSE_A] = RequiredCourseRow(course_id=_COURSE_A, title="A")
    certs.statuses[(_STUDENT, _COURSE_A)] = "valid"
    return svc


def test_motivation_over_8000_400() -> None:
    svc = _eligible_svc()
    with pytest.raises(BadRequest):
        svc.submit(
            valid_submit_body(motivation="x" * 8001),
            user_sub=_STUDENT,
            role="student",
        )


def test_unknown_country_400() -> None:
    svc = _eligible_svc()
    with pytest.raises(BadRequest):
        svc.submit(
            valid_submit_body(country="Narnia"),
            user_sub=_STUDENT,
            role="student",
        )


def test_unknown_research_area_400() -> None:
    svc = _eligible_svc()
    with pytest.raises(BadRequest):
        svc.submit(
            valid_submit_body(researchAreas=["Alchemy"]),
            user_sub=_STUDENT,
            role="student",
        )


def test_acknowledgement_false_400() -> None:
    svc = _eligible_svc()
    with pytest.raises(BadRequest):
        svc.submit(
            valid_submit_body(acknowledgement=False),
            user_sub=_STUDENT,
            role="student",
        )
