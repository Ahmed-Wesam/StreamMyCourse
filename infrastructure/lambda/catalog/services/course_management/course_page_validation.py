"""Validate and normalize course marketing page documents (RS-7)."""

from __future__ import annotations

import json
import re
from typing import Any

from services.common.errors import BadRequest

_MAX_UTF8_BYTES = 16 * 1024
_CAP_LIST_ITEM = 160
_CAP_HEADING = 120
_CAP_LEAD_NOTE = 500
_CAP_BODY = 400
_CAP_SUBTITLE = 500
_CAP_LEVEL = 40

_TAG_LIKE = re.compile(r"<[a-zA-Z/!]")

_TOP_LEVEL_KEYS = frozenset(
    {
        "subtitle",
        "level",
        "estimatedHours",
        "catalogSkills",
        "curriculumLead",
        "problem",
        "outcomes",
        "inside",
        "handsOn",
        "highlights",
        "audience",
        "assessment",
        "enrollCta",
    }
)

_LIST_SECTION_KEYS = frozenset({"heading", "lead", "items"})
_PROBLEM_KEYS = _LIST_SECTION_KEYS | frozenset({"calloutTitle", "calloutBody"})
_TEXT_CARD_KEYS = frozenset({"title", "body"})
_HANDS_ON_KEYS = frozenset({"heading", "lead", "cards", "closingNote"})
_HIGHLIGHTS_KEYS = frozenset({"heading", "lead", "items", "closingNote"})
_ASSESSMENT_KEYS = frozenset({"heading", "lead", "steps"})
_ENROLL_CTA_KEYS = frozenset({"heading", "body", "extraLine"})


def reject_tag_like(value: str, *, field: str) -> None:
    """Reject strings that look like HTML or XML tags. Plain text such as ``p < 0.05`` is allowed."""
    if _TAG_LIKE.search(value):
        raise BadRequest(f"Invalid markup in {field}")


def _reject_tag_like(value: str, *, field: str) -> None:
    reject_tag_like(value, field=field)


def _trim_cap(value: str, cap: int, *, field: str) -> str:
    _reject_tag_like(value, field=field)
    trimmed = value.strip()
    if len(trimmed) > cap:
        trimmed = trimmed[:cap]
    return trimmed


def _normalize_string(value: Any, cap: int, *, field: str) -> str | None:
    if not isinstance(value, str):
        raise BadRequest(f"{field} must be a string")
    trimmed = _trim_cap(value, cap, field=field)
    return trimmed if trimmed else None


def _normalize_string_list(items: Any, *, field: str) -> list[str] | None:
    if not isinstance(items, list):
        raise BadRequest(f"{field} must be an array")
    out: list[str] = []
    for i, raw in enumerate(items):
        if not isinstance(raw, str):
            raise BadRequest(f"{field} items must be strings")
        trimmed = _trim_cap(raw, _CAP_LIST_ITEM, field=f"{field}[{i}]")
        if trimmed:
            out.append(trimmed)
    return out if out else None


def _normalize_text_cards(cards: Any, *, field: str) -> list[dict[str, str]] | None:
    if not isinstance(cards, list):
        raise BadRequest(f"{field} must be an array")
    out: list[dict[str, str]] = []
    for i, raw in enumerate(cards):
        if not isinstance(raw, dict):
            raise BadRequest(f"{field}[{i}] must be an object")
        unknown = set(raw.keys()) - _TEXT_CARD_KEYS
        if unknown:
            raise BadRequest(f"Unknown keys in {field}[{i}]: {', '.join(sorted(unknown))}")
        card: dict[str, str] = {}
        if "title" in raw:
            title = _normalize_string(raw["title"], _CAP_HEADING, field=f"{field}[{i}].title")
            if title:
                card["title"] = title
        if "body" in raw:
            body = _normalize_string(raw["body"], _CAP_BODY, field=f"{field}[{i}].body")
            if body:
                card["body"] = body
        if card:
            out.append(card)
    return out if out else None


def _normalize_list_section(raw: Any, *, field: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise BadRequest(f"{field} must be an object")
    unknown = set(raw.keys()) - _LIST_SECTION_KEYS
    if unknown:
        raise BadRequest(f"Unknown keys in {field}: {', '.join(sorted(unknown))}")
    section: dict[str, Any] = {}
    if "heading" in raw:
        heading = _normalize_string(raw["heading"], _CAP_HEADING, field=f"{field}.heading")
        if heading:
            section["heading"] = heading
    if "lead" in raw:
        lead = _normalize_string(raw["lead"], _CAP_LEAD_NOTE, field=f"{field}.lead")
        if lead:
            section["lead"] = lead
    if "items" in raw:
        items = _normalize_string_list(raw["items"], field=f"{field}.items")
        if items:
            section["items"] = items
    return section if section else None


def _normalize_problem_section(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise BadRequest("problem must be an object")
    unknown = set(raw.keys()) - _PROBLEM_KEYS
    if unknown:
        raise BadRequest(f"Unknown keys in problem: {', '.join(sorted(unknown))}")
    section: dict[str, Any] = {}
    base = _normalize_list_section({k: raw[k] for k in raw if k in _LIST_SECTION_KEYS}, field="problem")
    if base:
        section.update(base)
    if "calloutTitle" in raw:
        title = _normalize_string(raw["calloutTitle"], _CAP_HEADING, field="problem.calloutTitle")
        if title:
            section["calloutTitle"] = title
    if "calloutBody" in raw:
        body = _normalize_string(raw["calloutBody"], _CAP_BODY, field="problem.calloutBody")
        if body:
            section["calloutBody"] = body
    return section if section else None


def _normalize_hands_on(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise BadRequest("handsOn must be an object")
    unknown = set(raw.keys()) - _HANDS_ON_KEYS
    if unknown:
        raise BadRequest(f"Unknown keys in handsOn: {', '.join(sorted(unknown))}")
    section: dict[str, Any] = {}
    if "heading" in raw:
        heading = _normalize_string(raw["heading"], _CAP_HEADING, field="handsOn.heading")
        if heading:
            section["heading"] = heading
    if "lead" in raw:
        lead = _normalize_string(raw["lead"], _CAP_LEAD_NOTE, field="handsOn.lead")
        if lead:
            section["lead"] = lead
    if "cards" in raw:
        cards = _normalize_text_cards(raw["cards"], field="handsOn.cards")
        if cards:
            section["cards"] = cards
    if "closingNote" in raw:
        note = _normalize_string(raw["closingNote"], _CAP_LEAD_NOTE, field="handsOn.closingNote")
        if note:
            section["closingNote"] = note
    return section if section else None


def _normalize_highlights(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise BadRequest("highlights must be an object")
    unknown = set(raw.keys()) - _HIGHLIGHTS_KEYS
    if unknown:
        raise BadRequest(f"Unknown keys in highlights: {', '.join(sorted(unknown))}")
    section: dict[str, Any] = {}
    if "heading" in raw:
        heading = _normalize_string(raw["heading"], _CAP_HEADING, field="highlights.heading")
        if heading:
            section["heading"] = heading
    if "lead" in raw:
        lead = _normalize_string(raw["lead"], _CAP_LEAD_NOTE, field="highlights.lead")
        if lead:
            section["lead"] = lead
    if "items" in raw:
        items = _normalize_string_list(raw["items"], field="highlights.items")
        if items:
            section["items"] = items
    if "closingNote" in raw:
        note = _normalize_string(raw["closingNote"], _CAP_LEAD_NOTE, field="highlights.closingNote")
        if note:
            section["closingNote"] = note
    return section if section else None


def _normalize_assessment(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise BadRequest("assessment must be an object")
    unknown = set(raw.keys()) - _ASSESSMENT_KEYS
    if unknown:
        raise BadRequest(f"Unknown keys in assessment: {', '.join(sorted(unknown))}")
    section: dict[str, Any] = {}
    if "heading" in raw:
        heading = _normalize_string(raw["heading"], _CAP_HEADING, field="assessment.heading")
        if heading:
            section["heading"] = heading
    if "lead" in raw:
        lead = _normalize_string(raw["lead"], _CAP_LEAD_NOTE, field="assessment.lead")
        if lead:
            section["lead"] = lead
    if "steps" in raw:
        steps = _normalize_text_cards(raw["steps"], field="assessment.steps")
        if steps:
            section["steps"] = steps
    return section if section else None


def _normalize_enroll_cta(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise BadRequest("enrollCta must be an object")
    unknown = set(raw.keys()) - _ENROLL_CTA_KEYS
    if unknown:
        raise BadRequest(f"Unknown keys in enrollCta: {', '.join(sorted(unknown))}")
    section: dict[str, Any] = {}
    if "heading" in raw:
        heading = _normalize_string(raw["heading"], _CAP_HEADING, field="enrollCta.heading")
        if heading:
            section["heading"] = heading
    if "body" in raw:
        body = _normalize_string(raw["body"], _CAP_BODY, field="enrollCta.body")
        if body:
            section["body"] = body
    if "extraLine" in raw:
        extra = _normalize_string(raw["extraLine"], _CAP_LEAD_NOTE, field="enrollCta.extraLine")
        if extra:
            section["extraLine"] = extra
    return section if section else None


def _normalize_estimated_hours(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BadRequest("estimatedHours must be an integer between 1 and 200")
    if value < 1 or value > 200:
        raise BadRequest("estimatedHours must be an integer between 1 and 200")
    return value


def _stored_has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _stored_list_has_text(items: Any) -> bool:
    if not isinstance(items, list):
        return False
    return any(_stored_has_text(item) for item in items)


def _stored_cards_have_text(cards: Any) -> bool:
    if not isinstance(cards, list):
        return False
    for card in cards:
        if not isinstance(card, dict):
            continue
        if _stored_has_text(card.get("title")) or _stored_has_text(card.get("body")):
            return True
    return False


def _stored_list_section_has_text(section: Any) -> bool:
    if not isinstance(section, dict):
        return False
    return (
        _stored_has_text(section.get("heading"))
        or _stored_has_text(section.get("lead"))
        or _stored_list_has_text(section.get("items"))
    )


def section_has_text(section_key: str, page: dict[str, Any]) -> bool:
    """Read-only visibility check for stored page JSON (must not raise on legacy/corrupt rows)."""
    if section_key == "problem":
        section = page.get("problem")
        if not isinstance(section, dict):
            return False
        if _stored_list_section_has_text(section):
            return True
        return _stored_has_text(section.get("calloutTitle")) or _stored_has_text(
            section.get("calloutBody")
        )
    if section_key in ("outcomes", "inside", "audience"):
        return _stored_list_section_has_text(page.get(section_key))
    if section_key == "handsOn":
        section = page.get("handsOn")
        if not isinstance(section, dict):
            return False
        return (
            _stored_has_text(section.get("heading"))
            or _stored_has_text(section.get("lead"))
            or _stored_cards_have_text(section.get("cards"))
            or _stored_has_text(section.get("closingNote"))
        )
    if section_key == "highlights":
        section = page.get("highlights")
        if not isinstance(section, dict):
            return False
        return (
            _stored_has_text(section.get("heading"))
            or _stored_has_text(section.get("lead"))
            or _stored_list_has_text(section.get("items"))
            or _stored_has_text(section.get("closingNote"))
        )
    if section_key == "assessment":
        section = page.get("assessment")
        if not isinstance(section, dict):
            return False
        return (
            _stored_has_text(section.get("heading"))
            or _stored_has_text(section.get("lead"))
            or _stored_cards_have_text(section.get("steps"))
        )
    if section_key == "enrollCta":
        section = page.get("enrollCta")
        if not isinstance(section, dict):
            return False
        return (
            _stored_has_text(section.get("heading"))
            or _stored_has_text(section.get("body"))
            or _stored_has_text(section.get("extraLine"))
        )
    return False


def validate_and_normalize_course_page(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BadRequest("page must be an object")
    unknown_top = set(raw.keys()) - _TOP_LEVEL_KEYS
    if unknown_top:
        raise BadRequest(f"Unknown keys in page: {', '.join(sorted(unknown_top))}")

    out: dict[str, Any] = {}
    if "subtitle" in raw:
        subtitle = _normalize_string(raw["subtitle"], _CAP_SUBTITLE, field="subtitle")
        if subtitle:
            out["subtitle"] = subtitle
    if "level" in raw:
        if not isinstance(raw["level"], str):
            raise BadRequest("level must be a string")
        _reject_tag_like(raw["level"], field="level")
        level_trimmed = raw["level"].strip()
        if len(level_trimmed) > _CAP_LEVEL:
            raise BadRequest("level exceeds maximum length")
        if level_trimmed:
            out["level"] = level_trimmed
    if "estimatedHours" in raw:
        hours = _normalize_estimated_hours(raw["estimatedHours"])
        if hours is not None:
            out["estimatedHours"] = hours
    if "catalogSkills" in raw:
        skills = _normalize_string_list(raw["catalogSkills"], field="catalogSkills")
        if skills:
            out["catalogSkills"] = skills
    if "curriculumLead" in raw:
        lead = _normalize_string(raw["curriculumLead"], _CAP_LEAD_NOTE, field="curriculumLead")
        if lead:
            out["curriculumLead"] = lead

    section_normalizers = {
        "problem": _normalize_problem_section,
        "outcomes": lambda v: _normalize_list_section(v, field="outcomes"),
        "inside": lambda v: _normalize_list_section(v, field="inside"),
        "handsOn": _normalize_hands_on,
        "highlights": _normalize_highlights,
        "audience": lambda v: _normalize_list_section(v, field="audience"),
        "assessment": _normalize_assessment,
        "enrollCta": _normalize_enroll_cta,
    }
    for key, normalizer in section_normalizers.items():
        if key in raw:
            normalized = normalizer(raw[key])
            if normalized:
                out[key] = normalized

    encoded = json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > _MAX_UTF8_BYTES:
        raise BadRequest("page content exceeds maximum size")
    return out
