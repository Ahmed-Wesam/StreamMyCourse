"""Domain types for question banks and module quizzes (RDS camelCase fields)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class QuestionBank:
    id: str
    courseId: str
    name: Optional[str]
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


@dataclass(frozen=True)
class PublishedQuestionGradingRow:
    """Published question fields needed to grade or recap a submission (service-internal)."""

    id: str
    promptText: str
    optionsJson: str
    correctOptionKey: str


@dataclass(frozen=True)
class ModuleQuizAttempt:
    """Persisted module-quiz attempt with presentation shuffle (RDS camelCase)."""

    id: str
    bindingId: str
    attemptNumber: int
    status: str
    shuffledQuestionOrder: list[str]
    shuffledChoiceOrders: dict[str, list[str]]
    startedAt: str
    submittedAt: Optional[str] = None


@dataclass(frozen=True)
class ModuleQuizSubmissionSnapshot:
    """One row from ``module_quiz_attempt_submissions`` with attempt metadata."""

    attemptId: str
    attemptNumber: int
    answersJson: dict[str, str]
    correctCount: int
    totalCount: int
    submittedAt: str


@dataclass(frozen=True)
class ModuleQuizAttemptBindingContext:
    """Attempt joined to binding + module quiz (authz / path checks in later slices)."""

    attempt: ModuleQuizAttempt
    moduleQuizId: str
    courseId: str
    moduleId: str
    userSub: str