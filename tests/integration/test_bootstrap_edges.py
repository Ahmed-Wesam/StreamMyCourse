"""S1 edge / bootstrap tests: OPTIONS preflight, 404 unknown route,
400 on malformed input, CORS origin echo."""

from __future__ import annotations

from helpers.api import ApiClient


# --- OPTIONS preflight ---------------------------------------------------------


def test_options_returns_cors_preflight(api: ApiClient):
    resp = api.options("/courses", origin="http://localhost:5173")
    assert resp.status_code == 204
    headers = {k.lower(): v for k, v in resp.headers.items()}
    assert "access-control-allow-origin" in headers
    assert "access-control-allow-methods" in headers
    assert "access-control-allow-headers" in headers


def test_options_unknown_origin_gets_first_allowlisted_origin(api: ApiClient):
    """Integ uses an explicit origin allowlist; unknown Origins get the first allowlisted value."""
    resp = api.options("/courses", origin="http://example.test")
    assert resp.status_code == 204
    headers = {k.lower(): v for k, v in resp.headers.items()}
    assert headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_options_without_origin_returns_default_allowlist_origin(api: ApiClient):
    resp = api.options("/courses", origin=None)
    assert resp.status_code == 204
    headers = {k.lower(): v for k, v in resp.headers.items()}
    assert headers.get("access-control-allow-origin") == "http://localhost:5173"


# --- Unknown route / method (handled by API Gateway, not the Lambda) ----------
# API Gateway pre-filters unconfigured paths/methods before Lambda is invoked,
# so the Lambda's NotFound branch is only reachable via direct invoke. What we
# *can* validate via HTTP is that GatewayResponses still attach CORS headers
# even on those 4xx error paths.


def test_unknown_route_returns_4xx_with_cors_headers(api: ApiClient):
    resp = api.raw.get("/this-route-does-not-exist", headers={"Origin": "http://example.test"})
    assert 400 <= resp.status_code < 500, f"expected 4xx from API Gateway, got {resp.status_code}"
    headers = {k.lower(): v for k, v in resp.headers.items()}
    # API Gateway GatewayResponses may still use * while Lambda OPTIONS uses the allowlist;
    # accept either pattern so this stays stable across stack parameter tweaks.
    assert "access-control-allow-origin" in headers
    assert headers.get("access-control-allow-origin") in (
        "*",
        "http://localhost:5173",
        "http://example.test",
    )


def test_unknown_method_on_known_path_returns_4xx(api: ApiClient):
    resp = api.raw.patch("/courses")  # PATCH /courses is not configured in API Gateway
    assert 400 <= resp.status_code < 500, f"expected 4xx from API Gateway, got {resp.status_code}"


# --- 400 malformed body --------------------------------------------------------


def test_malformed_json_body_returns_400(api: ApiClient):
    """parse_json_body should reject non-JSON bodies on POST /courses."""
    resp = api.raw.post(
        "/courses",
        content="this is not json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("code") == "bad_request"


def test_json_array_body_returns_400(api: ApiClient):
    """parse_json_body requires a JSON object, not an array."""
    resp = api.raw.post(
        "/courses",
        content="[1,2,3]",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("code") == "bad_request"


# --- 400 missing required fields on /upload-url --------------------------------


def test_upload_url_missing_course_id_returns_400(api: ApiClient):
    resp = api.raw.post(
        "/upload-url",
        json={"lessonId": "anything", "filename": "x.mp4", "contentType": "video/mp4"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("code") == "bad_request"
    assert "courseId" in body.get("message", "")


def test_upload_url_missing_lesson_id_returns_400(api: ApiClient):
    resp = api.raw.post(
        "/upload-url",
        json={"courseId": "anything", "filename": "x.mp4", "contentType": "video/mp4"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("code") == "bad_request"
    assert "lessonId" in body.get("message", "")
