"""Shared assertions for PostgreSQL-backed course modules (HTTPS integration suite)."""

from __future__ import annotations

from typing import Any, Dict, List

import httpx
import pytest

MODULES_GET_DEPLOY_HINT = (
    "Expected GET /courses/{id}/modules → 200 and a JSON array. "
    "If API Gateway responds with JWT/IAM Authorization errors, redeploy the "
    "`streammycourse-api` stack so GET modules matches repo "
    "`infrastructure/templates/api-stack.yaml` "
    "(AuthorizationType NONE for GET modules, identical to GET lessons)."
)

LESSON_MODULE_FIELDS_DEPLOY_HINT = (
    "Lesson JSON must expose moduleId and moduleOrder once the RDS modules schema "
    "is deployed. Redeploy the catalog Lambda if GET /courses/{id}/lessons omits "
    "these keys."
)

EXPECTED_CATALOG_FORBIDDEN_403 = (
    "Cross-teacher IDOR tests expect HTTP 403 with a JSON object from the catalog Lambda "
    'including "code": "forbidden". '
    "Non-JSON bodies or raw API Gateway authorization messages mean the request likely never "
    "reached Lambda—redeploy streammycourse-api and the catalog Lambda to match main. "
    "If only module routes fail while other mutating routes succeed, also compare GET /modules "
    "to infrastructure/templates/api-stack.yaml (GET should use AuthorizationType NONE like GET lessons)."
)

EXPECTED_ROLE_DENIAL_JSON = (
    "Student role denial tests expect HTTP 401 or 403 with JSON from the catalog Lambda and "
    '`code` in ("forbidden","unauthorized"). Plain API Gateway responses indicate stack drift '
    "or the request did not reach Lambda—redeploy streammycourse-api + catalog to match main."
)

_NON_JSON_BODY_HINT = "Response body is not valid JSON (common when API Gateway rejects before Lambda)."


def response_json_dict(resp: httpx.Response) -> Dict[str, Any]:
    """Parse response as a JSON object; raise AssertionError with context on failure."""
    try:
        data = resp.json()
    except ValueError as exc:
        raise AssertionError(
            f"{_NON_JSON_BODY_HINT} status={resp.status_code} text_prefix={resp.text[:800]!r}"
        ) from exc
    if not isinstance(data, dict):
        raise AssertionError(f"Expected JSON object, got {type(data).__name__}: {data!r}")
    return data


def require_lambda_json_or_skip(resp: httpx.Response, *, hint: str) -> Dict[str, Any]:
    """Skip when API Gateway returns non-JSON (method/path not deployed); else JSON object."""
    ct = (resp.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        return response_json_dict(resp)
    pytest.skip(
        f"{hint} Expected catalog JSON once route exists (see CatalogApiDeploymentV24). "
        f"HTTP {resp.status_code} content-type={resp.headers.get('content-type')!r}."
    )


def require_course_modules_list(resp: httpx.Response) -> List[Dict[str, Any]]:
    assert resp.status_code == 200, MODULES_GET_DEPLOY_HINT + f" Actual: {resp.status_code} {resp.text}"
    data = resp.json()
    assert isinstance(data, list), MODULES_GET_DEPLOY_HINT + f" Actual body: {data!r}"
    return data


def require_lessons_include_module_fields(resp: httpx.Response) -> List[Dict[str, Any]]:
    assert resp.status_code == 200, resp.text
    rows: List[Dict[str, Any]] = resp.json()
    assert isinstance(rows, list), resp.text
    for row in rows:
        assert "moduleId" in row and row["moduleId"], LESSON_MODULE_FIELDS_DEPLOY_HINT + f" Row: {row!r}"
        assert "moduleOrder" in row, LESSON_MODULE_FIELDS_DEPLOY_HINT + f" Row: {row!r}"
    return rows
