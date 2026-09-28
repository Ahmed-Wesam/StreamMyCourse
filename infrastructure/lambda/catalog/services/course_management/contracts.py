from __future__ import annotations

from typing import Any, Dict, List, Literal, NotRequired, TypedDict

from services.course_management.course_page_validation import section_has_text

_DETAIL_SECTION_KEYS = (
    "problem",
    "outcomes",
    "inside",
    "handsOn",
    "highlights",
    "audience",
    "assessment",
    "enrollCta",
)


class CourseDto(TypedDict):
    id: str
    title: str
    description: str
    status: Literal["DRAFT", "PUBLISHED"]
    createdAt: NotRequired[str]
    updatedAt: NotRequired[str]
    thumbnailUrl: NotRequired[str]
    hasAccess: NotRequired[bool]
    enrolled: NotRequired[bool]
    priceAmountMinor: NotRequired[int]
    subtitle: NotRequired[str]
    level: NotRequired[str]
    estimatedHours: NotRequired[int]
    catalogSkills: NotRequired[List[str]]
    curriculumLead: NotRequired[str]
    problem: NotRequired[Dict[str, Any]]
    outcomes: NotRequired[Dict[str, Any]]
    inside: NotRequired[Dict[str, Any]]
    handsOn: NotRequired[Dict[str, Any]]
    highlights: NotRequired[Dict[str, Any]]
    audience: NotRequired[Dict[str, Any]]
    assessment: NotRequired[Dict[str, Any]]
    enrollCta: NotRequired[Dict[str, Any]]


class LessonDto(TypedDict):
    id: str
    title: str
    order: int
    moduleId: str
    moduleOrder: int
    videoStatus: Literal["pending", "ready", "failed"]
    duration: NotRequired[int]
    thumbnailUrl: NotRequired[str]


class ModuleQuizDto(TypedDict):
    available: bool
    servedCountN: int
    latestScorePercent: NotRequired[int]


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


class S3PlaybackResponse(TypedDict):
    provider: Literal["s3"]
    playbackUrl: str


class KinescopePlaybackResponse(TypedDict):
    provider: Literal["kinescope"]
    videoId: str
    drmAuthToken: str
    watermarkText: str


PlaybackResponse = S3PlaybackResponse | KinescopePlaybackResponse


class UploadUrlResponse(TypedDict):
    uploadUrl: str
    uploadMethod: NotRequired[Literal["post", "tus"]]
    videoKey: NotRequired[str]
    thumbnailKey: NotRequired[str]
    provider: NotRequired[Literal["s3", "kinescope"]]


class MarkThumbnailReadyResponse(TypedDict):
    id: str
    thumbnailReady: bool


class CreateLessonFileResponse(TypedDict):
    fileId: str
    uploadUrl: str


class CompleteLessonFileResponse(TypedDict):
    fileId: str
    status: Literal["ready"]


class LessonFileListItem(TypedDict):
    fileId: str
    title: str
    kind: Literal["resource", "download"]
    fileType: str
    byteSize: int
    status: Literal["pending", "ready"]
    createdAt: NotRequired[str]


class LessonFileDownloadUrlResponse(TypedDict):
    url: str


class DeleteLessonFileResponse(TypedDict):
    fileId: str
    deleted: bool


def _page_from_obj(obj: Dict[str, Any]) -> dict[str, Any]:
    raw = obj.get("pageContent")
    if isinstance(raw, dict):
        return raw
    return {}


def _merge_page_card_fields(dto: CourseDto, page: dict[str, Any]) -> None:
    if page.get("subtitle"):
        dto["subtitle"] = str(page["subtitle"])
    if page.get("level"):
        dto["level"] = str(page["level"])
    if page.get("estimatedHours") is not None:
        dto["estimatedHours"] = int(page["estimatedHours"])
    skills = page.get("catalogSkills")
    if isinstance(skills, list) and skills:
        dto["catalogSkills"] = [str(s) for s in skills]
    if page.get("curriculumLead"):
        dto["curriculumLead"] = str(page["curriculumLead"])


def _merge_page_detail_sections(dto: CourseDto, page: dict[str, Any]) -> None:
    for key in _DETAIL_SECTION_KEYS:
        if section_has_text(key, page):
            section = page.get(key)
            if isinstance(section, dict):
                dto[key] = section  # type: ignore[literal-required]


def as_course_dto(obj: Dict[str, Any], *, detail: bool = False) -> CourseDto:
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
    if "hasAccess" in obj and obj.get("hasAccess") is not None:
        dto["hasAccess"] = bool(obj.get("hasAccess"))
    if "enrolled" in obj and obj.get("enrolled") is not None:
        dto["enrolled"] = bool(obj.get("enrolled"))
    if obj.get("priceAmountMinor") is not None:
        dto["priceAmountMinor"] = int(obj.get("priceAmountMinor"))
    page = _page_from_obj(obj)
    _merge_page_card_fields(dto, page)
    if detail:
        _merge_page_detail_sections(dto, page)
    return dto


def as_lesson_dto(obj: Dict[str, Any]) -> LessonDto:
    mid_raw = obj.get("moduleId")
    mid = str(mid_raw).strip() if mid_raw is not None else ""
    if not mid:
        raise ValueError("lesson DTO requires non-empty moduleId")
    if "moduleOrder" not in obj or obj.get("moduleOrder") is None:
        raise ValueError("lesson DTO requires moduleOrder")

    vs = obj.get("videoStatus", "pending")
    if vs not in ("pending", "ready", "failed"):
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
    return [as_course_dto(x, detail=False) for x in items]


def as_lesson_list(items: List[Dict[str, Any]]) -> List[LessonDto]:
    return [as_lesson_dto(x) for x in items]


def as_lesson_file_dto(obj: Dict[str, Any]) -> LessonFileListItem:
    dto: LessonFileListItem = {
        "fileId": str(obj.get("fileId", "")),
        "title": str(obj.get("title", "")),
        "kind": obj.get("kind", "resource"),  # type: ignore[typeddict-item]
        "fileType": str(obj.get("fileType", "")),
        "byteSize": int(obj.get("byteSize", 0) or 0),
        "status": obj.get("status", "pending"),  # type: ignore[typeddict-item]
    }
    if obj.get("createdAt") is not None:
        dto["createdAt"] = str(obj.get("createdAt", ""))
    return dto


def as_lesson_file_list(items: List[Dict[str, Any]]) -> List[LessonFileListItem]:
    return [as_lesson_file_dto(x) for x in items]


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
        mq_dto: ModuleQuizDto = {
            "available": bool(mq.get("available")),
            "servedCountN": int(mq.get("servedCountN", 0) or 0),
        }
        latest_pct = mq.get("latestScorePercent")
        if latest_pct is not None:
            mq_dto["latestScorePercent"] = int(latest_pct)
        dto["moduleQuiz"] = mq_dto
    return dto


def as_course_module_list(items: List[Dict[str, Any]]) -> List[CourseModuleDto]:
    return [as_course_module_dto(x) for x in items]
