"""API Gateway path resolution for video provider edge routing."""

from __future__ import annotations

from typing import Any, Dict

_API_ROOTS = frozenset({"courses", "playback", "upload-url", "users", "webhooks"})


def _strip_api_stage_prefix(stage: object, path: str) -> str:
    if not isinstance(stage, str) or not stage:
        return path
    prefix = f"/{stage}/"
    if path.startswith(prefix):
        return "/" + path[len(prefix) :]
    if path in (f"/{stage}", f"/{stage}/"):
        return "/"
    return path


def _strip_leading_stage_segment(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] not in _API_ROOTS and parts[1] in _API_ROOTS:
        return "/" + "/".join(parts[1:])
    return path


def _normalize_gateway_path(stage: object, path: str) -> str:
    return _strip_leading_stage_segment(_strip_api_stage_prefix(stage, path))


def apigw_routing_path(event: Dict[str, Any]) -> str:
    """Literal routing path (no ``{courseId}`` placeholders from resourcePath templates)."""
    rc = event.get("requestContext") or {}
    stage = rc.get("stage")
    resource_path = rc.get("resourcePath")
    if (
        isinstance(resource_path, str)
        and resource_path.startswith("/")
        and "{" not in resource_path
    ):
        return _normalize_gateway_path(stage, resource_path)

    path = event.get("path")
    raw = event.get("rawPath")
    for candidate in (path, raw):
        if isinstance(candidate, str) and candidate.startswith("/") and "{" not in candidate:
            return _normalize_gateway_path(stage, candidate)
    for candidate in (path, raw):
        if isinstance(candidate, str) and candidate.startswith("/"):
            return _normalize_gateway_path(stage, candidate)
    return "/"
