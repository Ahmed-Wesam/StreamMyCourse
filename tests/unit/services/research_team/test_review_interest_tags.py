"""RS-16: teacher application review includes the applicant's saved interest tags."""

from __future__ import annotations

import pytest

from services.common.errors import Forbidden
from services.research_team.ports import ApplicationRow
from tests.unit.services.research_team.helpers import make_app_row, make_service


def test_admin_review_returns_research_interest_tags() -> None:
    svc, repo, *_ = make_service()
    row = make_app_row()
    tagged = ApplicationRow(
        **{
            **row.__dict__,
            "research_interest_tags": ("surgical_research", "clinical_research"),
        }
    )
    repo.rows.append(tagged)
    body = svc.get_application(tagged.id, role="admin")
    assert body["researchInterestTags"] == ["surgical_research", "clinical_research"]
    listed = svc.list_applications(role="admin")["applications"]
    assert listed[0]["researchInterestTags"] == ["surgical_research", "clinical_research"]


def test_student_cannot_read_review( ) -> None:
    svc, repo, *_ = make_service()
    row = make_app_row()
    repo.rows.append(row)
    with pytest.raises(Forbidden):
        svc.get_application(row.id, role="student")
    with pytest.raises(Forbidden):
        svc.list_applications(role="student")
