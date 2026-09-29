"""Ports and persistence DTOs for assignments (RS-13)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class ObjectHead:
    content_type: str
    content_length: int


@dataclass(frozen=True)
class CriterionRow:
    id: str
    assignment_id: str
    label: str
    max_points: int
    sort_order: int


@dataclass(frozen=True)
class AssignmentRow:
    id: str
    course_id: str
    module_id: str
    title: str
    status: str
    pass_percent: int
    counts_toward_certificate: bool
    instructions_mode: str
    instructions_text: str
    instructions_html: str
    instructions_image_key: str
    instructions_image_ready: bool
    rubric_mode: str
    rubric_text: str
    rubric_html: str
    rubric_image_key: str
    rubric_image_ready: bool
    created_at: datetime
    updated_at: datetime
    criteria: tuple[CriterionRow, ...] = ()


@dataclass(frozen=True)
class SubmissionFileRow:
    id: str
    submission_id: str
    assignment_id: str
    course_id: str
    title: str
    file_type: str
    object_key: str
    content_type: str
    byte_size: int
    status: str
    created_at: datetime


@dataclass(frozen=True)
class GradeScoreRow:
    criterion_id: str
    points: int


@dataclass(frozen=True)
class GradeRow:
    id: str
    submission_id: str
    assignment_id: str
    course_id: str
    score_percent: int
    pass_percent: int
    passed: bool
    feedback: str
    graded_by: str
    graded_at: datetime
    scores: tuple[GradeScoreRow, ...] = ()


@dataclass(frozen=True)
class SubmissionRow:
    id: str
    assignment_id: str
    course_id: str
    user_sub: str
    status: str
    note: str
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    files: tuple[SubmissionFileRow, ...] = ()
    grade: Optional[GradeRow] = None


@dataclass(frozen=True)
class CourseOwnerInfo:
    id: str
    title: str
    created_by: str


@dataclass(frozen=True)
class NotifyMailMessage:
    kind: str
    to: str
    subject: str
    body: str


class AssignmentStoragePort(Protocol):
    """S3 adapter surface; concrete implementation lives in storage.py (later slice)."""

    def presign_put(self, key: str, content_type: str, content_length: int) -> str:
        """Return a PUT URL for ``key`` signed for content type and length."""
        ...

    def head(self, key: str) -> Optional[ObjectHead]:
        """Return object metadata, or ``None`` if the object is missing."""
        ...

    def delete(self, key: str) -> None:
        ...

    def presign_get(
        self,
        key: str,
        *,
        disposition: str,
        download_filename: str,
        expires_seconds: int,
    ) -> str:
        ...


class MediaCleanupPort(Protocol):
    """Enqueue object keys for async S3 delete (media cleanup queue)."""

    def enqueue_object_keys(self, keys: Sequence[str]) -> None:
        ...

    def queue_url(self) -> str:
        """Empty string when MEDIA_CLEANUP_QUEUE_URL is unset."""
        ...


class AssignmentMailPort(Protocol):
    def enqueue_notify(self, message: NotifyMailMessage) -> None:
        ...


class UserEmailPort(Protocol):
    def get_email_for_user_sub(self, user_sub: str) -> str:
        """Return ``users.email`` or empty string when missing."""
        ...


class CourseAccessPort(Protocol):
    def has_course_access(self, user_sub: str, course_id: str, role: str) -> bool:
        ...


class QuizLockPort(Protocol):
    def is_module_locked_for_student(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> bool:
        ...


class CourseLookupPort(Protocol):
    def get_course(self, course_id: str) -> Optional[CourseOwnerInfo]:
        ...

    def module_belongs_to_course(self, course_id: str, module_id: str) -> bool:
        ...


class CertificateIssuerPort(Protocol):
    """Optional RS-12 hook; duck-typed to CertificatesService.try_issue."""

    def try_issue(
        self, *, user_sub: str, course_id: str, role: str
    ) -> Optional[Any]:
        ...


class AssignmentsRepositoryPort(Protocol):
    def count_assignments_for_course(self, course_id: str) -> int:
        ...

    def list_assignments(
        self, course_id: str, *, published_only: bool = False
    ) -> List[AssignmentRow]:
        ...

    def get_assignment(
        self, course_id: str, assignment_id: str
    ) -> Optional[AssignmentRow]:
        ...

    def insert_assignment(
        self,
        *,
        course_id: str,
        module_id: str,
        title: str,
        pass_percent: int,
        counts_toward_certificate: bool,
        status: str = "draft",
    ) -> AssignmentRow:
        ...

    def update_assignment(self, row: AssignmentRow) -> AssignmentRow:
        ...

    def delete_assignment(self, course_id: str, assignment_id: str) -> bool:
        ...

    def list_object_keys_for_assignment(
        self, course_id: str, assignment_id: str
    ) -> List[str]:
        ...

    def list_object_keys_for_course(self, course_id: str) -> List[str]:
        """All assignment image and submission-file object keys for a course."""
        ...

    def replace_criteria(
        self,
        *,
        assignment_id: str,
        criteria: Sequence[tuple[str, str, int]],
    ) -> List[CriterionRow]:
        """Replace all criteria. Each tuple is (criterion_id, label, max_points)."""
        ...

    def list_criteria(self, assignment_id: str) -> List[CriterionRow]:
        ...

    def get_latest_submission_for_user(
        self, *, assignment_id: str, user_sub: str
    ) -> Optional[SubmissionRow]:
        ...

    def get_submission(
        self, *, course_id: str, assignment_id: str, submission_id: str
    ) -> Optional[SubmissionRow]:
        ...

    def list_submissions_for_assignment(
        self, *, course_id: str, assignment_id: str
    ) -> List[SubmissionRow]:
        ...

    def list_submissions_for_user(
        self, *, course_id: str, assignment_id: str, user_sub: str
    ) -> List[SubmissionRow]:
        ...

    def insert_submission(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_sub: str,
        status: str = "draft",
    ) -> SubmissionRow:
        ...

    def update_submission(self, row: SubmissionRow) -> SubmissionRow:
        ...

    def count_files_for_submission(self, submission_id: str) -> int:
        ...

    def insert_submission_file(
        self,
        *,
        file_id: str,
        submission_id: str,
        assignment_id: str,
        course_id: str,
        title: str,
        file_type: str,
        object_key: str,
        content_type: str,
        byte_size: int,
        status: str = "pending",
    ) -> SubmissionFileRow:
        ...

    def get_submission_file(
        self, *, submission_id: str, file_id: str
    ) -> Optional[SubmissionFileRow]:
        ...

    def mark_submission_file_ready(
        self, *, submission_id: str, file_id: str
    ) -> SubmissionFileRow:
        ...

    def insert_grade(
        self,
        *,
        submission_id: str,
        assignment_id: str,
        course_id: str,
        score_percent: int,
        pass_percent: int,
        passed: bool,
        feedback: str,
        graded_by: str,
        scores: Sequence[tuple[str, int]],
    ) -> GradeRow:
        """scores: sequence of (criterion_id, points). No update path (immutable)."""
        ...

    def get_grade_for_submission(self, submission_id: str) -> Optional[GradeRow]:
        ...
