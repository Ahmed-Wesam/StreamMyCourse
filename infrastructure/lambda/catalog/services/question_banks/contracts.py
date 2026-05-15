"""API JSON shapes for question-bank student routes."""

from __future__ import annotations

from typing import Any, List, TypedDict


class StudentQuizQuestionDto(TypedDict):
    id: str
    promptText: str
    optionsJson: Any


class StudentQuizStartDto(TypedDict):
    moduleQuizId: str
    moduleId: str
    servedCountN: int
    questions: List[StudentQuizQuestionDto]
