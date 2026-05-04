from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    id: str
    title: str
    description: str
    status: str
    createdAt: str = ""
    updatedAt: str = ""
    thumbnailKey: str = ""
    createdBy: str = ""


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    order: int
    videoKey: str = ""
    videoStatus: str = "pending"
    duration: int = 0
    thumbnailKey: str = ""


@dataclass(frozen=True)
class PresignResult:
    uploadUrl: str
    videoKey: str

