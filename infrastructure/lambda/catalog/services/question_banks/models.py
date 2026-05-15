"""Domain types for question banks and module quizzes (RDS camelCase fields)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class QuestionBank:
    id: str
    courseId: str
    status: str
    createdAt: str
    updatedAt: str


@dataclass(frozen=True)
class ModuleQuiz:
    id: str
    courseId: str
    moduleId: str
    questionBankId: Optional[str]
    servedCountN: Optional[int]
    createdAt: str
    updatedAt: str


@dataclass(frozen=True)
class Question:
    """Course question row (RDS camelCase); status is DRAFT or PUBLISHED at publish time."""

    id: str
    bankId: str
    status: str
    correctOptionKey: Optional[str] = None
    courseId: str = ""
    promptText: str = ""
    optionsJson: str = "[]"
    createdAt: str = ""
    updatedAt: str = ""


@dataclass(frozen=True)
class StudentModuleQuizBinding:
    """Persisted draw for one student + module quiz (question ids in draw order)."""

    id: str
    moduleQuizId: str
    courseId: str
    userSub: str
    questionIds: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BoundQuestion:
    """Student-safe question payload (no correctOptionKey or bank metadata)."""

    id: str
    promptText: str
    optionsJson: str
