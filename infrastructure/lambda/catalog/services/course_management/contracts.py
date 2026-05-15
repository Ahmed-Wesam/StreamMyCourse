from __future__ import annotations

from typing import Any, Dict, List, Literal, NotRequired, TypedDict


class CourseDto(TypedDict):
    id: str
    title: str
    description: str
    status: Literal["DRAFT", "PUBLISHED"]
    createdAt: NotRequired[str]
    updatedAt: NotRequired[str]
    thumbnailUrl: NotRequired[str]
    enrolled: NotRequired[bool]


class LessonDto(TypedDict):
    id: str
    title: str
    order: int
    moduleId: str
    moduleOrder: int
    videoStatus: Literal["pending", "ready"]
    duration: NotRequired[int]
    thumbnailUrl: NotRequired[str]


class ModuleQuizDto(TypedDict):
    available: bool
    servedCountN: int


class CourseModuleDto(TypedDict):
    id: str
    title: str
    description: str
    order: int
    createdAt: NotRequired[str]
    updatedAt: NotRequired[str]
    moduleQuiz: NotRequired[ModuleQuizDto]


class CreateCourseModuleResponse(TypedDict):
    moduleId: str
    order: int


class DeleteCourseModuleResponse(TypedDict):
    moduleId: str
    deleted: bool


class CreateCourseResponse(TypedDict):
    id: str
    status: str


class UpdateCourseResponse(TypedDict):
    id: str
    updated: bool


class DeleteCourseResponse(TypedDict):
    id: str
    deleted: bool


class PublishCourseResponse(TypedDict):
    id: str
    status: str


class CreateLessonResponse(TypedDict):
    lessonId: str
    moduleId: str
    order: int


class UpdateLessonResponse(TypedDict):
    lessonId: str
    updated: bool


class DeleteLessonResponse(TypedDict):
    lessonId: str
    deleted: bool


class MarkVideoReadyResponse(TypedDict):
    lessonId: str
    videoStatus: str


class PlaybackResponse(TypedDict):
    url: str


class UploadUrlResponse(TypedDict):
    uploadUrl: str
    videoKey: NotRequired[str]
    thumbnailKey: NotRequired[str]


class MarkThumbnailReadyResponse(TypedDict):
    id: str
    thumbnailReady: bool


def as_course_dto(obj: Dict[str, Any]) -> CourseDto:
    status = obj.get("status", "DRAFT")
    if status not in ("DRAFT", "PUBLISHED"):
        status = "DRAFT"
    dto: CourseDto = {
        "id": str(obj.get("id", "")),
        "title": str(obj.get("title", "")),
        "description": str(obj.get("description", "")),
        "status": status,  # type: ignore[assignment]
    }
    if obj.get("createdAt") is not None:
        dto["createdAt"] = str(obj.get("createdAt", ""))
    if obj.get("updatedAt") is not None:
        dto["updatedAt"] = str(obj.get("updatedAt", ""))
    if obj.get("thumbnailUrl"):
        dto["thumbnailUrl"] = str(obj.get("thumbnailUrl", ""))
    if "enrolled" in obj and obj.get("enrolled") is not None:
        dto["enrolled"] = bool(obj.get("enrolled"))
    return dto


def as_lesson_dto(obj: Dict[str, Any]) -> LessonDto:
    mid_raw = obj.get("moduleId")
    mid = str(mid_raw).strip() if mid_raw is not None else ""
    if not mid:
        raise ValueError("lesson DTO requires non-empty moduleId")
    if "moduleOrder" not in obj or obj.get("moduleOrder") is None:
        raise ValueError("lesson DTO requires moduleOrder")

    vs = obj.get("videoStatus", "pending")
    if vs not in ("pending", "ready"):
        vs = "pending"
    dto: LessonDto = {
        "id": str(obj.get("id", "")),
        "title": str(obj.get("title", "")),
        "order": int(obj.get("order", 0) or 0),
        "moduleId": mid,
        "moduleOrder": int(obj.get("moduleOrder", 0) or 0),
        "videoStatus": vs,  # type: ignore[assignment]
    }
    if "duration" in obj and obj.get("duration") is not None:
        dto["duration"] = int(obj.get("duration", 0) or 0)
    if obj.get("thumbnailUrl"):
        dto["thumbnailUrl"] = str(obj.get("thumbnailUrl", ""))
    return dto


def as_course_list(items: List[Dict[str, Any]]) -> List[CourseDto]:
    return [as_course_dto(x) for x in items]


def as_lesson_list(items: List[Dict[str, Any]]) -> List[LessonDto]:
    return [as_lesson_dto(x) for x in items]


def as_course_module_dto(obj: Dict[str, Any]) -> CourseModuleDto:
    dto: CourseModuleDto = {
        "id": str(obj.get("id", "")),
        "title": str(obj.get("title", "")),
        "description": str(obj.get("description", "")),
        "order": int(obj.get("order", 0) or 0),
    }
    if obj.get("createdAt") is not None:
        dto["createdAt"] = str(obj.get("createdAt", ""))
    if obj.get("updatedAt") is not None:
        dto["updatedAt"] = str(obj.get("updatedAt", ""))
    if obj.get("moduleQuiz") is not None:
        mq = obj["moduleQuiz"]
        dto["moduleQuiz"] = {
            "available": bool(mq.get("available")),
            "servedCountN": int(mq.get("servedCountN", 0) or 0),
        }
    return dto


def as_course_module_list(items: List[Dict[str, Any]]) -> List[CourseModuleDto]:
    return [as_course_module_dto(x) for x in items]
