from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class LessonProgressRow:
    lesson_id: str
    course_id: str
    user_sub: str
    completed: bool
    completed_at_iso: Optional[str]
    last_position_sec: int


class LessonProgressRepositoryPort(Protocol):
    def list_for_course(self, *, user_sub: str, course_id: str) -> List[LessonProgressRow]: ...

    def upsert(
        self,
        *,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        last_position_sec: int,
        completed: bool,
        completed_at_iso: Optional[str],
    ) -> None: ...
