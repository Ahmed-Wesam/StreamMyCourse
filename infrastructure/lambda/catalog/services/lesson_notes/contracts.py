from __future__ import annotations

from typing import List, NotRequired, TypedDict


class LessonNoteItem(TypedDict):
    id: str
    courseId: str
    lessonId: str
    body: str
    timestampSec: NotRequired[int]
    createdAt: str
    updatedAt: str


class ListLessonNotesResponse(TypedDict):
    notes: List[LessonNoteItem]


class LessonNoteResponse(TypedDict):
    note: LessonNoteItem


class DeleteLessonNoteResponse(TypedDict):
    ok: bool
