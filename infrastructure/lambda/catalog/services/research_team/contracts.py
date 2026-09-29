"""Request/response shaping and validation for research team (RS-14)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, TypedDict

from services.auth.profile_allowlists import COUNTRIES
from services.common.errors import BadRequest
from services.research_team.models import (
    CAP_COUNT,
    CAP_FULL_NAME,
    CAP_INSTITUTION,
    CAP_INTERESTS,
    CAP_MOTIVATION,
    CAP_POSITION,
    EXPERIENCE_LEVELS,
    MAX_RESEARCH_AREAS,
    RESEARCH_AREAS_SET,
    STATUSES,
    WEEKLY_HOURS,
)
from services.research_team.ports import ApplicationRow

_COUNTRY_SET = frozenset(COUNTRIES)


class RequiredCourseItem(TypedDict):
    id: str
    title: str


class RequirementsResponse(TypedDict):
    courses: List[RequiredCourseItem]


class MeCourseItem(TypedDict):
    courseId: str
    title: str
    certified: bool


class ApplicationJson(TypedDict):
    id: str
    status: str
    reapplyAllowed: bool
    submittedAt: str
    fullName: str
    email: str
    country: str
    institution: str
    position: str
    publicationCount: int
    projectCount: int
    statsExperience: str
    sysReviewExperience: str
    researchAreas: List[str]
    interests: str
    motivation: str
    weeklyHours: str
    acknowledgedAt: str


class AdminApplicationJson(ApplicationJson):
    userSub: str


class MeResearchTeamResponse(TypedDict):
    courses: List[MeCourseItem]
    eligible: bool
    canSubmit: bool
    application: Optional[ApplicationJson]


def strip_crlf(value: str) -> str:
    return value.replace("\r", "").replace("\n", "")


def _require_str(body: Mapping[str, Any], field: str, *, cap: int) -> str:
    if field not in body:
        raise BadRequest(f"Missing required field: {field}")
    raw = body[field]
    if not isinstance(raw, str):
        raise BadRequest(f"{field} must be a string")
    cleaned = strip_crlf(raw).strip()
    if not cleaned:
        raise BadRequest(f"{field} is required")
    if len(cleaned) > cap:
        raise BadRequest(f"{field} is too long")
    return cleaned


def _require_int(body: Mapping[str, Any], field: str) -> int:
    if field not in body:
        raise BadRequest(f"Missing required field: {field}")
    raw = body[field]
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise BadRequest(f"{field} must be an integer")
    if raw < 0 or raw > CAP_COUNT:
        raise BadRequest(f"{field} must be between 0 and {CAP_COUNT}")
    return raw


def _require_enum(body: Mapping[str, Any], field: str, allowed: frozenset[str]) -> str:
    if field not in body:
        raise BadRequest(f"Missing required field: {field}")
    raw = body[field]
    if not isinstance(raw, str) or raw not in allowed:
        raise BadRequest(f"Invalid {field}")
    return raw


def parse_submit_body(body: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate POST body. Ignores any email field."""
    full_name = _require_str(body, "fullName", cap=CAP_FULL_NAME)
    country = _require_enum(body, "country", _COUNTRY_SET)
    institution = _require_str(body, "institution", cap=CAP_INSTITUTION)
    position = _require_str(body, "position", cap=CAP_POSITION)
    publication_count = _require_int(body, "publicationCount")
    project_count = _require_int(body, "projectCount")
    stats_experience = _require_enum(body, "statsExperience", EXPERIENCE_LEVELS)
    sys_review_experience = _require_enum(body, "sysReviewExperience", EXPERIENCE_LEVELS)
    interests = _require_str(body, "interests", cap=CAP_INTERESTS)
    motivation = _require_str(body, "motivation", cap=CAP_MOTIVATION)
    weekly_hours = _require_enum(body, "weeklyHours", WEEKLY_HOURS)

    if "acknowledgement" not in body:
        raise BadRequest("Missing required field: acknowledgement")
    ack = body["acknowledgement"]
    if ack is not True:
        raise BadRequest("acknowledgement must be true")

    research_areas: list[str] = []
    if "researchAreas" in body and body["researchAreas"] is not None:
        raw_areas = body["researchAreas"]
        if not isinstance(raw_areas, list):
            raise BadRequest("researchAreas must be a list")
        if len(raw_areas) > MAX_RESEARCH_AREAS:
            raise BadRequest("Too many researchAreas")
        for item in raw_areas:
            if not isinstance(item, str) or item not in RESEARCH_AREAS_SET:
                raise BadRequest("Invalid researchAreas value")
            research_areas.append(item)

    return {
        "full_name": full_name,
        "country": country,
        "institution": institution,
        "position": position,
        "publication_count": publication_count,
        "project_count": project_count,
        "stats_experience": stats_experience,
        "sys_review_experience": sys_review_experience,
        "research_areas": tuple(research_areas),
        "interests": interests,
        "motivation": motivation,
        "weekly_hours": weekly_hours,
    }


def parse_patch_status(body: Mapping[str, Any]) -> str:
    if "status" not in body:
        raise BadRequest("Missing required field: status")
    raw = body["status"]
    if not isinstance(raw, str) or raw not in STATUSES:
        raise BadRequest("Invalid status")
    return raw


def parse_requirement_body(body: Mapping[str, Any]) -> bool:
    if "required" not in body:
        raise BadRequest("Missing required field: required")
    raw = body["required"]
    if not isinstance(raw, bool):
        raise BadRequest("required must be a boolean")
    return raw


def _iso(dt) -> str:
    if hasattr(dt, "isoformat"):
        text = dt.isoformat()
        if text.endswith("+00:00"):
            return text[:-6] + "Z"
        return text
    return str(dt)


def application_to_json(row: ApplicationRow) -> ApplicationJson:
    return {
        "id": row.id,
        "status": row.status,
        "reapplyAllowed": row.reapply_allowed,
        "submittedAt": _iso(row.submitted_at),
        "fullName": row.full_name,
        "email": row.email,
        "country": row.country,
        "institution": row.institution,
        "position": row.position,
        "publicationCount": row.publication_count,
        "projectCount": row.project_count,
        "statsExperience": row.stats_experience,
        "sysReviewExperience": row.sys_review_experience,
        "researchAreas": list(row.research_areas),
        "interests": row.interests,
        "motivation": row.motivation,
        "weeklyHours": row.weekly_hours,
        "acknowledgedAt": _iso(row.acknowledged_at),
    }


def application_to_admin_json(row: ApplicationRow) -> AdminApplicationJson:
    base = application_to_json(row)
    return {**base, "userSub": row.user_sub}  # type: ignore[return-value]
