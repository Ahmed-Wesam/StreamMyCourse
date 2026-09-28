from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class LessonNoteRow:
    """Persistence DTO for a row from ``lesson_notes``."""

    id: str
    user_sub: str
    course_id: str
    lesson_id: str
    body: str
    timestamp_sec: Optional[int]
    created_at: datetime
    updated_at: datetime


class LessonNotesRepositoryPort(Protocol):
    def list_notes_for_lesson(
        self, *, user_sub: str, course_id: str, lesson_id: str
    ) -> List[LessonNoteRow]:
        ...

    def count_notes_for_user_lesson(self, *, user_sub: str, lesson_id: str) -> int:
        ...

    def get_note_for_user(self, *, note_id: str, user_sub: str) -> Optional[LessonNoteRow]:
        ...

    def insert_note(
        self,
        *,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        body: str,
        timestamp_sec: Optional[int],
    ) -> LessonNoteRow:
        ...

    def update_note(
        self,
        *,
        note_id: str,
        user_sub: str,
        body: str,
        timestamp_sec: Optional[int],
    ) -> LessonNoteRow:
        ...

    def delete_note(self, *, note_id: str, user_sub: str) -> bool:
        ...
