"""Validate assignment request fields and sanitize rich HTML (stdlib only)."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence

from services.assignments.models import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ALLOWED_SUBMISSION_FILE_TYPES,
    CONTENT_TYPE_FOR_FILE_TYPE,
    DEFAULT_PASS_PERCENT,
    EXT_FOR_IMAGE_CONTENT_TYPE,
    IMAGE_SLOTS,
    MAX_CRITERION_LABEL_LEN,
    MAX_CRITERION_MAX_POINTS,
    MAX_FEEDBACK_LEN,
    MAX_IMAGE_BYTES,
    MAX_NOTE_LEN,
    MAX_PASS_PERCENT,
    MAX_PLAIN_OR_RICH_LEN,
    MAX_SUBMISSION_FILE_BYTES,
    MAX_TITLE_LEN,
    MIN_CRITERION_LABEL_LEN,
    MIN_CRITERION_MAX_POINTS,
    MIN_FEEDBACK_LEN,
    MIN_NOTE_LEN,
    MIN_PASS_PERCENT,
    MIN_TITLE_LEN,
    RICH_TEXT_ALLOWED_TAGS,
)
from services.common.errors import BadRequest

_TAG_LIKE = re.compile(r"<[a-zA-Z/!]")


def _is_https_href(href: str) -> bool:
    """True when href is an https URL with a host (no urllib; boundary-safe)."""
    value = (href or "").strip()
    if not value.lower().startswith("https://"):
        return False
    if "\r" in value or "\n" in value:
        return False
    host = value[8:].split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return bool(host)

# Client must never supply these; reject if present even when otherwise allowed.
_FORBIDDEN_CLIENT_KEYS = frozenset(
    {"objectKey", "passed", "scorePercent", "userSub", "to"}
)


def reject_unknown_keys(body: Mapping[str, Any], allowed: set[str] | frozenset[str]) -> None:
    if not isinstance(body, Mapping):
        raise BadRequest("Request body must be a JSON object")
    unknown = set(body.keys()) - set(allowed)
    forbidden = set(body.keys()) & _FORBIDDEN_CLIENT_KEYS
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise BadRequest(f"Unknown field(s): {names}")
    if unknown:
        names = ", ".join(sorted(unknown))
        raise BadRequest(f"Unknown field(s): {names}")


def reject_tag_like(value: str, *, field: str) -> None:
    if _TAG_LIKE.search(value):
        raise BadRequest(f"Invalid markup in {field}", code="invalid_markup")


def validate_title(title: Any) -> str:
    if not isinstance(title, str):
        raise BadRequest("title must be a string")
    trimmed = title.strip()
    if "\r" in trimmed or "\n" in trimmed:
        raise BadRequest("title must not contain line breaks", code="invalid_title")
    if len(trimmed) < MIN_TITLE_LEN or len(trimmed) > MAX_TITLE_LEN:
        raise BadRequest(
            f"title must be between {MIN_TITLE_LEN} and {MAX_TITLE_LEN} characters",
            code="invalid_title",
        )
    reject_tag_like(trimmed, field="title")
    return trimmed


def validate_plain_text(
    value: Any,
    *,
    field: str,
    min_len: int = 0,
    max_len: int = MAX_PLAIN_OR_RICH_LEN,
    required: bool = False,
) -> str:
    if value is None:
        if required:
            raise BadRequest(f"'{field}' is required")
        return ""
    if not isinstance(value, str):
        raise BadRequest(f"{field} must be a string")
    trimmed = value.strip() if required else value
    if required:
        trimmed = value.strip()
    if len(trimmed) < min_len:
        raise BadRequest(f"{field} is too short", code="invalid_text")
    if len(trimmed) > max_len:
        raise BadRequest(f"{field} is too long", code="invalid_text")
    if trimmed:
        reject_tag_like(trimmed, field=field)
    return trimmed


def validate_pass_percent(value: Any, *, default: int = DEFAULT_PASS_PERCENT) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise BadRequest("passPercent must be an integer", code="invalid_pass_percent")
    if value < MIN_PASS_PERCENT or value > MAX_PASS_PERCENT:
        raise BadRequest(
            f"passPercent must be between {MIN_PASS_PERCENT} and {MAX_PASS_PERCENT}",
            code="invalid_pass_percent",
        )
    return value


def validate_bool(value: Any, *, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise BadRequest(f"{field} must be a boolean")
    return value


def validate_criterion_label(label: Any) -> str:
    if not isinstance(label, str):
        raise BadRequest("criterion label must be a string")
    trimmed = label.strip()
    if (
        len(trimmed) < MIN_CRITERION_LABEL_LEN
        or len(trimmed) > MAX_CRITERION_LABEL_LEN
    ):
        raise BadRequest(
            f"criterion label must be between {MIN_CRITERION_LABEL_LEN} "
            f"and {MAX_CRITERION_LABEL_LEN} characters",
            code="invalid_criterion",
        )
    reject_tag_like(trimmed, field="criterion label")
    return trimmed


def validate_criterion_max_points(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BadRequest("maxPoints must be an integer", code="invalid_criterion")
    if value < MIN_CRITERION_MAX_POINTS or value > MAX_CRITERION_MAX_POINTS:
        raise BadRequest(
            f"maxPoints must be between {MIN_CRITERION_MAX_POINTS} "
            f"and {MAX_CRITERION_MAX_POINTS}",
            code="invalid_criterion",
        )
    return value


def validate_note(value: Any) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise BadRequest("note must be a string")
    trimmed = value.strip()
    if len(trimmed) < MIN_NOTE_LEN or len(trimmed) > MAX_NOTE_LEN:
        raise BadRequest(
            f"note must be between {MIN_NOTE_LEN} and {MAX_NOTE_LEN} characters",
            code="invalid_note",
        )
    reject_tag_like(trimmed, field="note")
    return trimmed


def validate_feedback(value: Any) -> str:
    if not isinstance(value, str):
        raise BadRequest("feedback must be a string")
    trimmed = value.strip()
    if len(trimmed) < MIN_FEEDBACK_LEN or len(trimmed) > MAX_FEEDBACK_LEN:
        raise BadRequest(
            f"feedback must be between {MIN_FEEDBACK_LEN} and {MAX_FEEDBACK_LEN} characters",
            code="invalid_feedback",
        )
    reject_tag_like(trimmed, field="feedback")
    return trimmed


def validate_image_upload(*, slot: Any, content_type: Any, byte_size: Any) -> tuple[str, str, int]:
    if not isinstance(slot, str) or slot not in IMAGE_SLOTS:
        raise BadRequest("slot must be 'instructions' or 'rubric'", code="invalid_slot")
    if not isinstance(content_type, str):
        raise BadRequest("contentType must be a string")
    norm = content_type.strip().lower().split(";", 1)[0].strip()
    if norm == "image/jpg":
        norm = "image/jpeg"
    if norm not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise BadRequest("Unsupported image contentType", code="invalid_content_type")
    if isinstance(byte_size, bool) or not isinstance(byte_size, int):
        raise BadRequest("byteSize must be an integer")
    if byte_size < 1 or byte_size > MAX_IMAGE_BYTES:
        raise BadRequest(
            f"byteSize must be between 1 and {MAX_IMAGE_BYTES}",
            code="invalid_byte_size",
        )
    return slot, norm, byte_size


def validate_submission_file_type(file_type: Any) -> str:
    if not isinstance(file_type, str):
        raise BadRequest("fileType must be a string")
    ft = file_type.strip().lower()
    if ft == "zip":
        raise BadRequest("zip uploads are not allowed", code="invalid_file_type")
    if ft not in ALLOWED_SUBMISSION_FILE_TYPES:
        raise BadRequest("Unsupported fileType", code="invalid_file_type")
    return ft


def validate_submission_byte_size(byte_size: Any) -> int:
    if isinstance(byte_size, bool) or not isinstance(byte_size, int):
        raise BadRequest("byteSize must be an integer")
    if byte_size < 1 or byte_size > MAX_SUBMISSION_FILE_BYTES:
        raise BadRequest(
            f"byteSize must be between 1 and {MAX_SUBMISSION_FILE_BYTES}",
            code="invalid_byte_size",
        )
    return byte_size


def content_type_for_file_type(file_type: str) -> str:
    return CONTENT_TYPE_FOR_FILE_TYPE[file_type]


def extension_for_image_content_type(content_type: str) -> str:
    return EXT_FOR_IMAGE_CONTENT_TYPE[content_type]


def sanitize_download_filename(title: str, *, extension: str) -> str:
    cleaned = (title or "").strip()
    for ch in ("\r", "\n", '"', ";", "\\"):
        cleaned = cleaned.replace(ch, "")
    if len(cleaned) > 120:
        cleaned = cleaned[:120]
    base = cleaned or "download"
    ext = (extension or "").strip().lstrip(".")
    if ext and not base.lower().endswith(f".{ext.lower()}"):
        return f"{base}.{ext}"
    return base


class _RichTextSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._open_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in ("script", "style", "iframe", "object", "embed"):
            self._skip_depth += 1
            return
        if t == "img":
            # Void forbidden tag — drop attributes (incl. onerror) and do not skip later content.
            return
        if self._skip_depth:
            return
        if t not in RICH_TEXT_ALLOWED_TAGS:
            return
        if t == "br":
            self._parts.append("<br>")
            return
        if t == "a":
            href = ""
            for name, value in attrs:
                if (name or "").lower() == "href" and value:
                    href = value.strip()
                    break
            if not _is_https_href(href):
                # Keep inner text; do not emit a dangerous anchor.
                self._open_stack.append("a-stripped")
                return
            safe_href = html.escape(href, quote=True)
            self._parts.append(f'<a href="{safe_href}">')
            self._open_stack.append("a")
            return
        self._parts.append(f"<{t}>")
        self._open_stack.append(t)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style", "iframe", "object", "embed"):
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if t == "img" or t == "br":
            return
        if self._skip_depth:
            return
        if t not in RICH_TEXT_ALLOWED_TAGS:
            return
        if not self._open_stack:
            return
        opened = self._open_stack.pop()
        if opened == "a-stripped":
            return
        if opened == "a":
            self._parts.append("</a>")
            return
        self._parts.append(f"</{opened}>")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._parts.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if self._skip_depth:
            return
        self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._skip_depth:
            return
        self._parts.append(f"&#{name};")

    def get_html(self) -> str:
        return "".join(self._parts)


def sanitize_rich_html(raw: Any) -> str:
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise BadRequest("html must be a string")
    if len(raw) > MAX_PLAIN_OR_RICH_LEN:
        raise BadRequest("html is too long", code="invalid_html")
    parser = _RichTextSanitizer()
    parser.feed(raw)
    parser.close()
    out = parser.get_html()
    if len(out) > MAX_PLAIN_OR_RICH_LEN:
        raise BadRequest("html is too long", code="invalid_html")
    return out


def score_percent_half_up(*, awarded: int, max_total: int) -> int:
    if max_total <= 0:
        raise BadRequest("maxTotal must be greater than 0")
    return (100 * awarded + max_total // 2) // max_total
