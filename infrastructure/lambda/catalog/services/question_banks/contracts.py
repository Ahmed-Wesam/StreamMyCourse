"""API JSON shapes for question-bank student routes."""

from __future__ import annotations

from typing import Any, List, Literal, NotRequired, TypedDict


class QuestionBankCreateRequestDto(TypedDict):
    name: str


class QuestionBankRenameRequestDto(TypedDict):
    name: str


class QuestionBankWriteResponseDto(TypedDict):
    questionBankId: str
    name: str


class PublisherQuestionBankSummaryDto(TypedDict):
    questionBankId: str
    name: str
    status: str
    createdAt: str
    updatedAt: str


class StudentQuizQuestionDto(TypedDict):
    id: str
    promptText: str
    optionsJson: Any


class StudentQuizStartInProgressDto(TypedDict):
    phase: Literal["in_progress"]
    moduleQuizId: str
    moduleId: str
    servedCountN: int
    attemptId: str
    attemptNumber: int
    questionIds: List[str]
    questions: List[StudentQuizQuestionDto]


class StudentQuizResultQuestionDto(TypedDict):
    id: str
    promptText: str
    selectedOptionKey: str
    correctOptionKey: str
    isCorrect: bool


class StudentQuizLatestSubmissionDto(TypedDict):
    correctCount: int
    totalCount: int
    attemptNumber: int
    submittedAt: NotRequired[str | None]
    questions: List[StudentQuizResultQuestionDto]


class StudentQuizStartLatestResultsDto(TypedDict):
    phase: Literal["latest_results"]
    moduleQuizId: str
    moduleId: str
    servedCountN: int
    latestSubmission: StudentQuizLatestSubmissionDto


class StudentQuizSubmitRequestDto(TypedDict):
    attemptId: str
    answers: dict[str, str]


class StudentQuizSubmitResponseDto(TypedDict):
    attemptId: str
    attemptNumber: int
    correctCount: int
    totalCount: int
    questions: List[StudentQuizResultQuestionDto]


class StudentQuizStartBodyDto(TypedDict, total=False):
    """Optional JSON body for ``POST .../quiz/start``."""

    retake: bool
