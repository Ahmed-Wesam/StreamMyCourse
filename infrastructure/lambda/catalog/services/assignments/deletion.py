"""Assignment submission deletion steps (DSQL-7a S5)."""

from __future__ import annotations

from typing import Protocol

from services.course_deletion.catalog import split_deletion_parent_id
from services.course_deletion.registry import CourseDeletionRegistry

_ASSIGNMENT_DELETION_ORDER = 400


class CertificateDeletionRepo(Protocol):
    def delete_certificates_for_course(self, course_id: str) -> int: ...

    def delete_certificates_for_user(self, user_sub: str) -> int: ...

    def delete_bundle_certificates_for_user(self, user_sub: str) -> int: ...


class ResearchTeamDeletionRepo(Protocol):
    def delete_research_team_applications_for_user(self, user_sub: str) -> int: ...


class AssignmentDeletionRepo(Protocol):
    def delete_assignment_grade_scores_for_user(self, user_sub: str) -> int: ...

    def delete_assignment_grades_for_user(self, user_sub: str) -> int: ...

    def delete_assignment_submission_files_for_user(self, user_sub: str) -> int: ...

    def delete_assignment_submissions_for_user(self, user_sub: str) -> int: ...

    def delete_assignment_grade_scores_for_course(self, course_id: str) -> int: ...

    def delete_assignment_grades_for_course(self, course_id: str) -> int: ...

    def delete_assignment_submission_files_for_course(self, course_id: str) -> int: ...

    def delete_assignment_submissions_for_course(self, course_id: str) -> int: ...

    def delete_assignment_grade_scores_for_module(
        self, course_id: str, module_id: str
    ) -> int: ...

    def delete_assignment_grades_for_module(self, course_id: str, module_id: str) -> int: ...

    def delete_assignment_submission_files_for_module(
        self, course_id: str, module_id: str
    ) -> int: ...

    def delete_assignment_submissions_for_module(
        self, course_id: str, module_id: str
    ) -> int: ...


def delete_assignment_children_for_user(repo: AssignmentDeletionRepo, user_sub: str) -> None:
    repo.delete_assignment_grade_scores_for_user(user_sub)
    repo.delete_assignment_grades_for_user(user_sub)
    repo.delete_assignment_submission_files_for_user(user_sub)
    repo.delete_assignment_submissions_for_user(user_sub)


def delete_assignment_certificate_research_rows_for_user(
    assignments_repo: AssignmentDeletionRepo,
    certificates_repo: CertificateDeletionRepo,
    research_repo: ResearchTeamDeletionRepo,
    user_sub: str,
) -> None:
    delete_assignment_children_for_user(assignments_repo, user_sub)
    certificates_repo.delete_certificates_for_user(user_sub)
    certificates_repo.delete_bundle_certificates_for_user(user_sub)
    research_repo.delete_research_team_applications_for_user(user_sub)


def delete_assignment_children_for_course(
    repo: AssignmentDeletionRepo, course_id: str
) -> None:
    repo.delete_assignment_grade_scores_for_course(course_id)
    repo.delete_assignment_grades_for_course(course_id)
    repo.delete_assignment_submission_files_for_course(course_id)
    repo.delete_assignment_submissions_for_course(course_id)


def delete_assignment_children_for_course_with_certificates(
    assignments_repo: AssignmentDeletionRepo,
    certificates_repo: CertificateDeletionRepo,
    course_id: str,
) -> None:
    delete_assignment_children_for_course(assignments_repo, course_id)
    certificates_repo.delete_certificates_for_course(course_id)


def delete_assignment_children_for_module(
    repo: AssignmentDeletionRepo, course_id: str, module_id: str
) -> None:
    repo.delete_assignment_grade_scores_for_module(course_id, module_id)
    repo.delete_assignment_grades_for_module(course_id, module_id)
    repo.delete_assignment_submission_files_for_module(course_id, module_id)
    repo.delete_assignment_submissions_for_module(course_id, module_id)


def register_assignment_deletion_steps(
    registry: CourseDeletionRegistry,
    repo: AssignmentDeletionRepo,
    certificates_repo: CertificateDeletionRepo | None = None,
) -> None:
    if certificates_repo is not None:
        course_run = lambda course_id: delete_assignment_children_for_course_with_certificates(
            repo, certificates_repo, course_id
        )
    else:
        course_run = lambda course_id: delete_assignment_children_for_course(repo, course_id)
    registry.register(
        name="assignment_rows_course",
        order=_ASSIGNMENT_DELETION_ORDER,
        scope="course",
        run=course_run,
    )
    registry.register(
        name="assignment_rows_module",
        order=_ASSIGNMENT_DELETION_ORDER,
        scope="module",
        run=lambda parent_id: delete_assignment_children_for_module(
            repo, *split_deletion_parent_id(parent_id)
        ),
    )


__all__ = [
    "AssignmentDeletionRepo",
    "CertificateDeletionRepo",
    "ResearchTeamDeletionRepo",
    "delete_assignment_certificate_research_rows_for_user",
    "delete_assignment_children_for_course",
    "delete_assignment_children_for_course_with_certificates",
    "delete_assignment_children_for_module",
    "delete_assignment_children_for_user",
    "register_assignment_deletion_steps",
]
