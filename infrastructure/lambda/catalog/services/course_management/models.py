from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Course:
    id: str
    title: str
    description: str
    status: str
    createdBy: str
    createdAt: str = ""
    updatedAt: str = ""
    thumbnailKey: str = ""
    priceAmountMinor: int | None = None
    pageContent: dict[str, Any] = field(default_factory=dict)
    certificateCode: str = ""


@dataclass(frozen=True)
class CourseModule:
    id: str
    courseId: str
    title: str
    description: str
    order: int
    createdAt: str = ""
    updatedAt: str = ""


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    order: int
    moduleId: str
    # moduleOrder = display sequence of parent module within the course (JOIN)
    moduleOrder: int = 0
    videoKey: str = ""
    videoStatus: str = "pending"
    duration: int = 0
    thumbnailKey: str = ""


@dataclass(frozen=True)
class PresignResult:
    uploadUrl: str
    videoKey: str


@dataclass(frozen=True)
class LessonFilePresignResult:
    uploadUrl: str
    objectKey: str


@dataclass(frozen=True)
class LessonFile:
    id: str
    courseId: str
    lessonId: str
    kind: str
    title: str
    objectKey: str
    contentType: str
    byteSize: int
    status: str
    fileType: str
    createdAt: str = ""

