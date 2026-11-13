"""DSQL-7b S3: certificate deletion at course/user order 400."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.assignments.deletion import (
    delete_assignment_children_for_course_with_certificates,
    delete_assignment_certificate_research_rows_for_user,
    register_assignment_deletion_steps,
)
from services.certificates.rds_repo import _DELETE_CERTIFICATES_FOR_COURSE_SQL
from services.course_deletion.registry import CourseDeletionRegistry
from services.course_deletion.runner import CourseDeletionRunner

_CID = "11111111-1111-4111-8111-111111111111"
_SUB = "user-sub-1"


class TestCertificateDeletionOrder:
    def test_course_callback_deletes_certificates_after_submissions(self) -> None:
        log: list[str] = []
        assignments = MagicMock()
        assignments.delete_assignment_grade_scores_for_course.side_effect = (
            lambda _: log.append("scores")
        )
        assignments.delete_assignment_grades_for_course.return_value = 0
        assignments.delete_assignment_submission_files_for_course.return_value = 0
        assignments.delete_assignment_submissions_for_course.side_effect = (
            lambda _: log.append("submissions")
        )
        certificates = MagicMock()
        certificates.delete_certificates_for_course.side_effect = (
            lambda _: log.append("certificates")
        )
        delete_assignment_children_for_course_with_certificates(
            assignments, certificates, _CID
        )
        assert log == ["scores", "submissions", "certificates"]

    def test_course_step_does_not_delete_bundle_certificates(self) -> None:
        certificates = MagicMock()
        registry = CourseDeletionRegistry()
        register_assignment_deletion_steps(
            registry, MagicMock(), certificates_repo=certificates
        )
        CourseDeletionRunner(registry).run("course", _CID)
        certificates.delete_bundle_certificates_for_user.assert_not_called()

    def test_user_callback_deletes_certificates_and_bundle(self) -> None:
        log: list[str] = []
        assignments = MagicMock()
        assignments.delete_assignment_grade_scores_for_user.side_effect = (
            lambda _: log.append("assignments")
        )
        assignments.delete_assignment_grades_for_user.return_value = 0
        assignments.delete_assignment_submission_files_for_user.return_value = 0
        assignments.delete_assignment_submissions_for_user.return_value = 0
        certificates = MagicMock()
        certificates.delete_certificates_for_user.side_effect = (
            lambda _: log.append("certs")
        )
        certificates.delete_bundle_certificates_for_user.side_effect = (
            lambda _: log.append("bundle")
        )
        research = MagicMock()
        research.delete_research_team_applications_for_user.side_effect = (
            lambda _: log.append("research")
        )
        delete_assignment_certificate_research_rows_for_user(
            assignments, certificates, research, _SUB
        )
        assert log == ["assignments", "certs", "bundle", "research"]


def test_delete_certificates_for_course_sql_uses_limit_1000() -> None:
    lowered = _DELETE_CERTIFICATES_FOR_COURSE_SQL.lower()
    assert "limit 1000" in lowered
    assert "using" in lowered
