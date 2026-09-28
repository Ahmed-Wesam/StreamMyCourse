"""Private per-lesson student notes (author-only CRUD)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from services.common.errors import BadRequest, Conflict, Forbidden, NotFound
from services.lesson_notes.contracts import (
    DeleteLessonNoteResponse,
    LessonNoteItem,
    LessonNoteResponse,
    ListLessonNotesResponse,
)
from services.lesson_notes.models import MAX_NOTES_PER_USER_LESSON
from services.lesson_notes.ports import LessonNoteRow, LessonNotesRepositoryPort
from services.lesson_notes.validation import validate_note_body, validate_timestamp_sec

if TYPE_CHECKING:
    from services.course_management.ports import (
        CourseCatalogRepositoryPort,
        StudentModuleLockPort,
    )
    from services.purchases.ports import CourseAccessPort


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except Exception:
        return False


def _note_to_item(row: LessonNoteRow) -> LessonNoteItem:
    item: LessonNoteItem = {
        "id": row.id,
        "courseId": row.course_id,
        "lessonId": row.lesson_id,
        "body": row.body,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }
    if row.timestamp_sec is not None:
        item["timestampSec"] = row.timestamp_sec
    return item


class LessonNotesService:
    def __init__(
        self,
        notes_repo: LessonNotesRepositoryPort,
        course_access: "CourseAccessPort",
        course_repo: "CourseCatalogRepositoryPort",
        module_lock: "StudentModuleLockPort | None" = None,
    ) -> None:
        self._notes_repo = notes_repo
        self._course_access = course_access
        self._course_repo = course_repo
        self._module_lock = module_lock

    def _check_authorization(self, user_sub: str, course_id: str, role: str) -> bool:
        return self._course_access.has_course_access(user_sub, course_id, role)

    def _ensure_lesson_access(
        self,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        *,
        role: str,
    ) -> None:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")

        if not self._check_authorization(user_sub, course_id, role):
            raise Forbidden(
                "Purchase required to access lesson notes",
                code="purchase_required",
            )

        lesson = self._course_repo.get_lesson_by_id(course_id, lesson_id)
        if lesson is None:
            raise NotFound("Lesson not found")

        if self._module_lock is not None and self._module_lock.is_module_locked_for_student(
            course_id,
            lesson.moduleId,
            cognito_sub=user_sub,
            role=role,
        ):
            raise Forbidden(
                "Complete the prior module quiz to unlock this content",
                code="module_locked",
            )

    def _get_owned_note(
        self,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        note_id: str,
    ) -> LessonNoteRow:
        if not _is_valid_uuid(note_id):
            raise NotFound("Note not found")
        row = self._notes_repo.get_note_for_user(note_id=note_id, user_sub=user_sub)
        if row is None:
            raise NotFound("Note not found")
        if row.course_id != course_id or row.lesson_id != lesson_id:
            raise NotFound("Note not found")
        return row

    def list_notes(
        self,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        *,
        role: str = "student",
    ) -> ListLessonNotesResponse:
        self._ensure_lesson_access(user_sub, course_id, lesson_id, role=role)
        rows = self._notes_repo.list_notes_for_lesson(
            user_sub=user_sub,
            course_id=course_id,
            lesson_id=lesson_id,
        )
        return {"notes": [_note_to_item(r) for r in rows]}

    def create_note(
        self,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        *,
        body: str,
        timestamp_sec: int | None,
        role: str = "student",
    ) -> LessonNoteResponse:
        self._ensure_lesson_access(user_sub, course_id, lesson_id, role=role)
        normalized_body = validate_note_body(body)
        ts = validate_timestamp_sec(timestamp_sec)

        count = self._notes_repo.count_notes_for_user_lesson(
            user_sub=user_sub,
            lesson_id=lesson_id,
        )
        if count >= MAX_NOTES_PER_USER_LESSON:
            raise Conflict(
                f"Maximum of {MAX_NOTES_PER_USER_LESSON} notes per lesson",
                code="note_limit_exceeded",
            )

        row = self._notes_repo.insert_note(
            user_sub=user_sub,
            course_id=course_id,
            lesson_id=lesson_id,
            body=normalized_body,
            timestamp_sec=ts,
        )
        return {"note": _note_to_item(row)}

    def update_note(
        self,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        note_id: str,
        *,
        body: Optional[str],
        timestamp_sec: Optional[int],
        clear_timestamp: bool,
        role: str = "student",
    ) -> LessonNoteResponse:
        self._ensure_lesson_access(user_sub, course_id, lesson_id, role=role)
        existing = self._get_owned_note(user_sub, course_id, lesson_id, note_id)

        new_body = existing.body
        if body is not None:
            new_body = validate_note_body(body)

        new_ts = existing.timestamp_sec
        if clear_timestamp:
            new_ts = None
        elif timestamp_sec is not None:
            new_ts = validate_timestamp_sec(timestamp_sec)

        if body is None and not clear_timestamp and timestamp_sec is None:
            raise BadRequest("No fields to update", code="bad_request")

        row = self._notes_repo.update_note(
            note_id=note_id,
            user_sub=user_sub,
            body=new_body,
            timestamp_sec=new_ts,
        )
        return {"note": _note_to_item(row)}

    def delete_note(
        self,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        note_id: str,
        *,
        role: str = "student",
    ) -> DeleteLessonNoteResponse:
        self._ensure_lesson_access(user_sub, course_id, lesson_id, role=role)
        self._get_owned_note(user_sub, course_id, lesson_id, note_id)
        self._notes_repo.delete_note(note_id=note_id, user_sub=user_sub)
        return {"ok": True}
