"""HTTP JSON shapes for certificates (RS-12)."""

from __future__ import annotations

from typing import List, NotRequired, TypedDict


class CertificatePublicItem(TypedDict):
    credentialId: str
    status: str
    studentName: str
    courseTitle: str
    issueDate: str


class CertificateMineItem(TypedDict):
    id: str
    credentialId: str
    status: str
    studentName: str
    courseTitle: str
    issueDate: str
    instructorName: str
    instructorTitle: str
    courseId: str


class InProgressItem(TypedDict):
    courseId: str
    courseTitle: str
    passedCount: int
    totalCount: int


class ProfileIncompleteItem(TypedDict):
    courseId: str
    courseTitle: str
    requirementsMet: bool
    message: str
    href: str


class MeCertificatesResponse(TypedDict):
    certificates: List[CertificateMineItem]
    inProgress: List[InProgressItem]
    profileIncomplete: List[ProfileIncompleteItem]


class NotFoundPublicBody(TypedDict):
    status: str
    credentialId: NotRequired[str]


class CourseCertificateItem(TypedDict):
    id: str
    credentialId: str
    status: str
    studentName: str
    courseTitle: str
    issueDate: str


class ListCourseCertificatesResponse(TypedDict):
    certificates: List[CourseCertificateItem]


class RevokeResponse(TypedDict):
    id: str
    credentialId: str
    status: str
