"""Domain types for question banks and module quizzes (RDS camelCase fields)."""

from __future__ import annotations

from dataclasses import dataclass
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
