"""HTTP JSON shapes for assignments (RS-13)."""

from __future__ import annotations

from typing import List, NotRequired, Optional, TypedDict


class ContentBlock(TypedDict):
    mode: str
    text: NotRequired[str]
    html: NotRequired[str]
    imageReady: NotRequired[bool]


class CriterionItem(TypedDict):
    id: str
    label: str
    maxPoints: int


class MyLatestItem(TypedDict):
    id: str
    status: str
    scorePercent: NotRequired[int]
    passed: NotRequired[bool]
    feedback: NotRequired[str]


class AssignmentItem(TypedDict):
    id: str
    title: str
    moduleId: str
    status: str
    passPercent: int
    countsTowardCertificate: bool
    locked: bool
    instructions: ContentBlock
    rubric: ContentBlock
    criteria: List[CriterionItem]
    myLatest: Optional[MyLatestItem]


class ListAssignmentsResponse(TypedDict):
    assignments: List[AssignmentItem]


class AssignmentResponse(TypedDict):
    assignment: AssignmentItem


class UploadUrlResponse(TypedDict):
    uploadUrl: str


class CreateFileResponse(TypedDict):
    fileId: str
    uploadUrl: str


class ImageUrlResponse(TypedDict):
    url: str


class FileUrlResponse(TypedDict):
    url: str


class SubmissionFileItem(TypedDict):
    id: str
    title: str
    fileType: str
    byteSize: int
    status: str


class GradeItem(TypedDict):
    scorePercent: int
    passed: bool
    feedback: str
    scores: List[dict]


class SubmissionItem(TypedDict):
    id: str
    status: str
    note: str
    files: List[SubmissionFileItem]
    grade: NotRequired[GradeItem]
    userSub: NotRequired[str]


class ListSubmissionsResponse(TypedDict):
    submissions: List[SubmissionItem]


class SubmissionResponse(TypedDict):
    submission: SubmissionItem


class GradeResponse(TypedDict):
    scorePercent: int
    passed: bool


class DeleteAssignmentResponse(TypedDict):
    ok: bool
