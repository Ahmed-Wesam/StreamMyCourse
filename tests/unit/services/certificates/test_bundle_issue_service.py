"""Bundle certificate issuance tests (fakes only; behavior lands in slice 2)."""

from __future__ import annotations

from itertools import cycle
from typing import Callable, Sequence
from uuid import uuid4

from services.certificates.eligibility import AssignmentRequirement, QuizRequirement
from services.certificates.models import INSTRUCTOR_NAME, INSTRUCTOR_TITLE
from services.certificates.ports import CertificateRow, CourseInfo
from tests.unit.services.certificates.test_issue_service import (
    _CREDENTIAL_RE,
    _FIXED_NOW,
    _STUDENT,
    _TEACHER,
    FakeCourseAccess,
    FakeCourseLookup,
    FakeEntitled,
    FakeProfile,
    FakeRepo,
    FakeRequirements,
    _build_service,
)


def _cycling_rng(values: Sequence[int]) -> Callable[[int], int]:
    it = cycle(values)

    def rng(_n: int) -> int:
        return next(it)

    return rng


def _default_pathway_rng() -> Callable[[int], int]:
    return _cycling_rng([9, 12, 2, 14, 1, 0, 11, 4, 13, 8])

_PATHWAY = (
    ("Research Methodology", "11111111-1111-1111-1111-111111111111", "16A001"),
    ("Statistics & SPSS", "22222222-2222-2222-2222-222222222222", "16A002"),
    ("Scientific Writing", "33333333-3333-3333-3333-333333333333", "16A003"),
    (
        "Systematic Reviews & Meta-Analysis",
        "44444444-4444-4444-4444-444444444444",
        "16A004",
    ),
)
_COURSE_RM_DUP = "55555555-5555-5555-5555-555555555555"
_BUNDLE_TITLE = "Research Mastery Bundle"
_PASSED_REQ = (
    [QuizRequirement(module_id="m1", passed=True)],
    [
        AssignmentRequirement(
            assignment_id="a1",
            status="published",
            counts_toward_certificate=True,
            passed=True,
        )
    ],
)


def _pathway_course_ids() -> list[str]:
    return [entry[1] for entry in _PATHWAY]


def _build_pathway_service(
    *,
    extra_courses: list[tuple[str, str, str]] | None = None,
    entitled_ids: list[str] | None = None,
    **overrides: object,
):
    course_lookup = FakeCourseLookup()
    course_lookup.courses.clear()
    for title, course_id, code in _PATHWAY:
        course_lookup.courses[course_id] = CourseInfo(
            id=course_id,
            title=title,
            created_by=_TEACHER,
            certificate_code=code,
        )
    if extra_courses:
        for title, course_id, code in extra_courses:
            course_lookup.courses[course_id] = CourseInfo(
                id=course_id,
                title=title,
                created_by=_TEACHER,
                certificate_code=code,
            )

    ids = entitled_ids if entitled_ids is not None else _pathway_course_ids()
    access = FakeCourseAccess()
    access.allowed = {(_STUDENT, cid) for cid in ids}

    entitled = FakeEntitled()
    entitled.by_user[_STUDENT] = list(ids)

    requirements = FakeRequirements()
    for cid in ids:
        requirements.by_course[cid] = _PASSED_REQ

    if "rng" not in overrides:
        overrides = {**overrides, "rng": _default_pathway_rng()}
    return _build_service(
        course_lookup=course_lookup,
        course_access=access,
        entitled_courses=entitled,
        requirements=requirements,
        **overrides,
    )


def _issue_for_course_ids(svc, course_ids: list[str]) -> list[CertificateRow]:
    rows: list[CertificateRow] = []
    for course_id in course_ids:
        row = svc.try_issue(user_sub=_STUDENT, course_id=course_id, role="student")
        assert row is not None
        rows.append(row)
    return rows


def _bundle_items(response: dict) -> list[dict]:
    return [c for c in response["certificates"] if c.get("kind") == "bundle"]


def test_four_pathway_certs_yields_one_bundle_in_list_mine() -> None:
    svc = _build_pathway_service()
    _issue_for_course_ids(svc, _pathway_course_ids())
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    bundles = _bundle_items(resp)
    assert len(bundles) == 1
    assert bundles[0].get("credentialId")
    assert bundles[0]["kind"] == "bundle"


def test_bundle_issues_when_fourth_course_cert_created_on_same_list_mine() -> None:
    svc = _build_pathway_service()
    _issue_for_course_ids(svc, _pathway_course_ids()[:3])
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    course_rows = [c for c in resp["certificates"] if c.get("kind") != "bundle"]
    assert len(course_rows) == 4
    assert len(_bundle_items(resp)) == 1


def test_three_pathway_certs_no_bundle_kind() -> None:
    three_ids = _pathway_course_ids()[:3]
    svc = _build_pathway_service(entitled_ids=three_ids)
    _issue_for_course_ids(svc, three_ids)
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    assert _bundle_items(resp) == []


def test_duplicate_pathway_title_two_course_ids_no_bundle() -> None:
    svc = _build_pathway_service(
        extra_courses=[
            ("Research Methodology", _COURSE_RM_DUP, "16A099"),
        ],
        entitled_ids=[
            _PATHWAY[0][1],
            _COURSE_RM_DUP,
            _PATHWAY[1][1],
            _PATHWAY[2][1],
        ],
    )
    _issue_for_course_ids(
        svc,
        [_PATHWAY[0][1], _COURSE_RM_DUP, _PATHWAY[1][1], _PATHWAY[2][1]],
    )
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    assert _bundle_items(resp) == []


def test_second_list_mine_same_bundle_credential_id() -> None:
    svc = _build_pathway_service()
    _issue_for_course_ids(svc, _pathway_course_ids())
    first = svc.list_mine(user_sub=_STUDENT, role="student")
    second = svc.list_mine(user_sub=_STUDENT, role="student")
    first_ids = [b["credentialId"] for b in _bundle_items(first)]
    second_ids = [b["credentialId"] for b in _bundle_items(second)]
    assert len(first_ids) == 1
    assert first_ids == second_ids


def test_revoke_pathway_cert_revokes_bundle_public_still_has_name() -> None:
    svc = _build_pathway_service()
    course_rows = _issue_for_course_ids(svc, _pathway_course_ids())
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    bundles = _bundle_items(resp)
    assert len(bundles) == 1
    bundle_cred = bundles[0]["credentialId"]

    svc.revoke(
        course_id=course_rows[0].course_id,
        certificate_id=course_rows[0].id,
        cognito_sub=_TEACHER,
        role="teacher",
    )
    after = svc.list_mine(user_sub=_STUDENT, role="student")
    after_bundles = _bundle_items(after)
    assert len(after_bundles) == 1
    assert after_bundles[0]["credentialId"] == bundle_cred
    assert after_bundles[0]["status"] == "revoked"

    public = svc.get_public(bundle_cred)
    assert public["studentName"]
    assert "userSub" not in public


def test_revoke_non_pathway_course_cert_leaves_bundle_valid() -> None:
    extra_id = "66666666-6666-6666-6666-666666666666"
    svc = _build_pathway_service(
        extra_courses=[("Advanced Stats", extra_id, "16A099")],
        entitled_ids=_pathway_course_ids() + [extra_id],
    )
    _issue_for_course_ids(svc, _pathway_course_ids())
    extra_row = svc.try_issue(user_sub=_STUDENT, course_id=extra_id, role="student")
    assert extra_row is not None
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    bundles = _bundle_items(resp)
    assert len(bundles) == 1
    assert bundles[0]["status"] == "valid"

    svc.revoke(
        course_id=extra_row.course_id,
        certificate_id=extra_row.id,
        cognito_sub=_TEACHER,
        role="teacher",
    )
    after = svc.list_mine(user_sub=_STUDENT, role="student")
    after_bundles = _bundle_items(after)
    assert len(after_bundles) == 1
    assert after_bundles[0]["status"] == "valid"


def test_public_bundle_course_title_and_no_user_sub() -> None:
    svc = _build_pathway_service()
    _issue_for_course_ids(svc, _pathway_course_ids())
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    bundles = _bundle_items(resp)
    assert len(bundles) == 1
    public = svc.get_public(bundles[0]["credentialId"])
    assert public["courseTitle"] == _BUNDLE_TITLE
    assert "userSub" not in public


def test_blank_profile_four_course_cert_rows_bundle_still_issued() -> None:
    repo = FakeRepo()
    profile = FakeProfile()
    profile.names[_STUDENT] = ("", "")
    for idx, (title, course_id, code) in enumerate(_PATHWAY):
        suffix = f"{idx:010X}"
        repo.insert_certificate(
            CertificateRow(
                id=str(uuid4()),
                user_sub=_STUDENT,
                course_id=course_id,
                credential_id=f"RS-{code}-2026-{suffix}",
                student_name="Ada Lovelace",
                course_title=title,
                issue_date=_FIXED_NOW.date(),
                instructor_name=INSTRUCTOR_NAME,
                instructor_title=INSTRUCTOR_TITLE,
                status="valid",
            )
        )
    svc = _build_pathway_service(repo=repo, profile=profile)
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    bundles = _bundle_items(resp)
    assert len(bundles) == 1
    assert bundles[0].get("studentName") == "Ada Lovelace"


def test_bundle_credential_id_matches_regex() -> None:
    svc = _build_pathway_service()
    _issue_for_course_ids(svc, _pathway_course_ids())
    resp = svc.list_mine(user_sub=_STUDENT, role="student")
    bundles = _bundle_items(resp)
    assert len(bundles) == 1
    assert _CREDENTIAL_RE.match(bundles[0]["credentialId"])
