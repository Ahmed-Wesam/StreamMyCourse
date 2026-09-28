"""RS-11 Slice 3: lesson notes service rules (author-only, access, limits)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Conflict, Forbidden, NotFound
from services.lesson_notes.ports import LessonNoteRow
from services.lesson_notes.service import LessonNotesService

_COURSE_ID = "11111111-1111-1111-1111-111111111111"
_LESSON_ID = "22222222-2222-2222-2222-222222222222"
_MODULE_ID = "33333333-3333-3333-3333-333333333333"
_NOTE_ID = "44444444-4444-4444-4444-444444444444"
_USER = "student-1"


def _note_row(
    *,
    note_id: str = _NOTE_ID,
    user_sub: str = _USER,
    body: str = "My note",
    timestamp_sec: int | None = 120,
) -> LessonNoteRow:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return LessonNoteRow(
        id=note_id,
        user_sub=user_sub,
        course_id=_COURSE_ID,
        lesson_id=_LESSON_ID,
        body=body,
        timestamp_sec=timestamp_sec,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def notes_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def course_access() -> MagicMock:
    m = MagicMock()
    m.has_course_access.return_value = True
    return m


@pytest.fixture
def course_repo() -> MagicMock:
    m = MagicMock()
    m.get_lesson_by_id.return_value = MagicMock(id=_LESSON_ID, moduleId=_MODULE_ID)
    return m


@pytest.fixture
def module_lock() -> MagicMock:
    m = MagicMock()
    m.is_module_locked_for_student.return_value = False
    return m


@pytest.fixture
def service(
    notes_repo: MagicMock,
    course_access: MagicMock,
    course_repo: MagicMock,
    module_lock: MagicMock,
) -> LessonNotesService:
    return LessonNotesService(
        notes_repo=notes_repo,
        course_access=course_access,
        course_repo=course_repo,
        module_lock=module_lock,
    )


class TestAccessAndLock:
    def test_list_requires_purchase(
        self,
        service: LessonNotesService,
        course_access: MagicMock,
        notes_repo: MagicMock,
    ) -> None:
        course_access.has_course_access.return_value = False
        with pytest.raises(Forbidden) as exc:
            service.list_notes(_USER, _COURSE_ID, _LESSON_ID, role="student")
        assert exc.value.code == "purchase_required"
        notes_repo.list_notes_for_lesson.assert_not_called()

    def test_list_raises_module_locked(
        self,
        service: LessonNotesService,
        module_lock: MagicMock,
        notes_repo: MagicMock,
    ) -> None:
        module_lock.is_module_locked_for_student.return_value = True
        with pytest.raises(Forbidden) as exc:
            service.list_notes(_USER, _COURSE_ID, _LESSON_ID, role="student")
        assert exc.value.code == "module_locked"
        notes_repo.list_notes_for_lesson.assert_not_called()

    def test_create_checks_module_lock(
        self,
        service: LessonNotesService,
        module_lock: MagicMock,
        notes_repo: MagicMock,
    ) -> None:
        module_lock.is_module_locked_for_student.return_value = True
        with pytest.raises(Forbidden) as exc:
            service.create_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                body="Hello",
                timestamp_sec=None,
                role="student",
            )
        assert exc.value.code == "module_locked"
        notes_repo.insert_note.assert_not_called()


class TestListNotes:
    def test_list_returns_notes(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        row = _note_row()
        notes_repo.list_notes_for_lesson.return_value = [row]

        result = service.list_notes(_USER, _COURSE_ID, _LESSON_ID, role="student")

        assert len(result["notes"]) == 1
        assert result["notes"][0]["id"] == _NOTE_ID
        assert result["notes"][0]["body"] == "My note"
        assert result["notes"][0]["timestampSec"] == 120
        notes_repo.list_notes_for_lesson.assert_called_once_with(
            user_sub=_USER,
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
        )


class TestCreateNote:
    def test_create_happy_path(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        notes_repo.count_notes_for_user_lesson.return_value = 0
        row = _note_row(body="New note", timestamp_sec=10)
        notes_repo.insert_note.return_value = row

        result = service.create_note(
            _USER,
            _COURSE_ID,
            _LESSON_ID,
            body="New note",
            timestamp_sec=10,
            role="student",
        )

        assert result["note"]["body"] == "New note"
        notes_repo.insert_note.assert_called_once()

    def test_create_rejects_empty_body(self, service: LessonNotesService) -> None:
        with pytest.raises(BadRequest):
            service.create_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                body="   ",
                timestamp_sec=None,
                role="student",
            )

    def test_create_rejects_tag_like_body(self, service: LessonNotesService) -> None:
        with pytest.raises(BadRequest) as exc:
            service.create_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                body="<script>alert(1)</script>",
                timestamp_sec=None,
                role="student",
            )
        assert exc.value.code == "invalid_markup"

    def test_create_rejects_body_over_4000(self, service: LessonNotesService) -> None:
        with pytest.raises(BadRequest):
            service.create_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                body="x" * 4001,
                timestamp_sec=None,
                role="student",
            )

    def test_create_rejects_invalid_timestamp(
        self,
        service: LessonNotesService,
    ) -> None:
        with pytest.raises(BadRequest) as exc:
            service.create_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                body="ok",
                timestamp_sec=86401,
                role="student",
            )
        assert exc.value.code == "invalid_timestamp"

    def test_create_rejects_when_at_limit(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        notes_repo.count_notes_for_user_lesson.return_value = 50
        with pytest.raises(Conflict) as exc:
            service.create_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                body="one more",
                timestamp_sec=None,
                role="student",
            )
        assert exc.value.code == "note_limit_exceeded"
        notes_repo.insert_note.assert_not_called()


class TestUpdateNote:
    def test_update_other_users_note_is_not_found(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        notes_repo.get_note_for_user.return_value = None
        with pytest.raises(NotFound):
            service.update_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                _NOTE_ID,
                body="changed",
                timestamp_sec=None,
                clear_timestamp=False,
                role="student",
            )

    def test_update_wrong_lesson_is_not_found(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        notes_repo.get_note_for_user.return_value = _note_row()
        with pytest.raises(NotFound):
            service.update_note(
                _USER,
                _COURSE_ID,
                "99999999-9999-9999-9999-999999999999",
                _NOTE_ID,
                body="changed",
                timestamp_sec=None,
                clear_timestamp=False,
                role="student",
            )

    def test_update_happy_path(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        notes_repo.get_note_for_user.return_value = _note_row()
        updated = _note_row(body="Updated")
        notes_repo.update_note.return_value = updated

        result = service.update_note(
            _USER,
            _COURSE_ID,
            _LESSON_ID,
            _NOTE_ID,
            body="Updated",
            timestamp_sec=None,
            clear_timestamp=False,
            role="student",
        )

        assert result["note"]["body"] == "Updated"
        notes_repo.update_note.assert_called_once()


class TestDeleteNote:
    def test_delete_missing_note_is_not_found(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        notes_repo.get_note_for_user.return_value = None
        with pytest.raises(NotFound):
            service.delete_note(
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                _NOTE_ID,
                role="student",
            )

    def test_delete_happy_path(
        self,
        service: LessonNotesService,
        notes_repo: MagicMock,
    ) -> None:
        notes_repo.get_note_for_user.return_value = _note_row()
        notes_repo.delete_note.return_value = True

        result = service.delete_note(
            _USER,
            _COURSE_ID,
            _LESSON_ID,
            _NOTE_ID,
            role="student",
        )

        assert result == {"ok": True}
        notes_repo.delete_note.assert_called_once_with(note_id=_NOTE_ID, user_sub=_USER)


class TestPathValidation:
    def test_invalid_course_uuid(self, service: LessonNotesService) -> None:
        with pytest.raises(NotFound):
            service.list_notes(_USER, "not-a-uuid", _LESSON_ID, role="student")

    def test_lesson_not_in_course(
        self,
        service: LessonNotesService,
        course_repo: MagicMock,
    ) -> None:
        course_repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.list_notes(_USER, _COURSE_ID, _LESSON_ID, role="student")
