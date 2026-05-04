from __future__ import annotations

import json

from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
    pick_origin,
)


class TestApigwRoutingPath:
    def test_prefers_resource_path_when_no_placeholders(self) -> None:
        evt = {
            "requestContext": {"resourcePath": "/users/me", "stage": "dev"},
            "path": "/dev/users/me",
        }
        assert apigw_routing_path(evt) == "/users/me"

    def test_ignores_resource_path_template_in_favor_of_literal_path(self) -> None:
        evt = {
            "requestContext": {
                "resourcePath": "/courses/{courseId}",
                "stage": "integ",
            },
            "path": "/integ/courses/abc-123",
        }
        assert apigw_routing_path(evt) == "/courses/abc-123"

    def test_falls_back_to_raw_path(self) -> None:
        evt = {"requestContext": {"http": {"method": "GET"}}, "rawPath": "/courses"}
        assert apigw_routing_path(evt) == "/courses"

    def test_strips_stage_from_path_when_no_resource_path(self) -> None:
        evt = {
            "requestContext": {"stage": "integ"},
            "path": "/integ/courses",
        }
        assert apigw_routing_path(evt) == "/courses"

    def test_prefers_literal_path_over_template_rawpath(self) -> None:
        evt = {
            "requestContext": {"stage": "integ", "resourcePath": "/courses/{courseId}"},
            "rawPath": "/courses/{courseId}",
            "path": "/integ/courses/abc-123",
        }
        assert apigw_routing_path(evt) == "/courses/abc-123"

    def test_heuristic_strips_stage_when_context_stage_missing(self) -> None:
        evt = {
            "requestContext": {},
            "path": "/integ/courses/xyz",
        }
        assert apigw_routing_path(evt) == "/courses/xyz"


class TestApigwCognitoClaims:
    def test_reads_nested_claims(self) -> None:
        evt = {
            "requestContext": {
                "authorizer": {"claims": {"sub": "abc", "email": "u@example.com"}}
            }
        }
        assert apigw_cognito_claims(evt) == {"sub": "abc", "email": "u@example.com"}

    def test_flattens_authorizer_root_claims(self) -> None:
        evt = {
            "requestContext": {
                "authorizer": {
                    "sub": "abc",
                    "email": "u@example.com",
                    "principalId": "user",
                }
            }
        }
        assert apigw_cognito_claims(evt) == {"sub": "abc", "email": "u@example.com"}

    def test_parses_stringified_claims_json(self) -> None:
        payload = json.dumps({"sub": "abc", "email": "u@example.com"})
        evt = {"requestContext": {"authorizer": {"claims": payload}}}
        assert apigw_cognito_claims(evt) == {"sub": "abc", "email": "u@example.com"}


class TestPickOrigin:
    def test_wildcard_with_request_origin_echoes_origin(self) -> None:
        # `["*"]` is "anything goes": when a request origin is supplied we
        # echo it (that's what browsers expect for credentialed-style flows).
        assert pick_origin(["*"], "https://example.com") == "https://example.com"

    def test_wildcard_without_request_origin_returns_star(self) -> None:
        assert pick_origin(["*"], None) == "*"
        assert pick_origin(["*"], "") == "*"

    def test_allowlisted_exact_match_echoes(self) -> None:
        allowed = ["https://app.example.com", "http://localhost:5173"]
        assert pick_origin(allowed, "http://localhost:5173") == "http://localhost:5173"

    def test_allowlisted_miss_returns_first_allowed(self) -> None:
        allowed = ["https://app.example.com", "http://localhost:5173"]
        assert pick_origin(allowed, "https://evil.example.com") == "https://app.example.com"

    def test_missing_origin_returns_first_allowed(self) -> None:
        allowed = ["https://app.example.com", "http://localhost:5173"]
        assert pick_origin(allowed, None) == "https://app.example.com"
        assert pick_origin(allowed, "") == "https://app.example.com"

    def test_empty_allowlist_returns_none(self) -> None:
        assert pick_origin([], "https://example.com") is None
        assert pick_origin([], None) is None


class TestJsonResponse:
    def test_status_body_and_cors_headers(self) -> None:
        resp = json_response(201, {"id": "abc"}, "https://app.example.com")

        assert resp["statusCode"] == 201
        assert json.loads(resp["body"]) == {"id": "abc"}

        headers = resp["headers"]
        assert headers["content-type"] == "application/json"
        assert headers["Access-Control-Allow-Origin"] == "https://app.example.com"
        assert "GET" in headers["Access-Control-Allow-Methods"]
        assert "POST" in headers["Access-Control-Allow-Methods"]
        assert "OPTIONS" in headers["Access-Control-Allow-Methods"]
        assert headers["Access-Control-Allow-Headers"] == "Content-Type,Authorization"
        assert "Content-Security-Policy" in headers
        assert "default-src 'none'" in headers["Content-Security-Policy"]
        assert "Strict-Transport-Security" in headers
        assert headers["Cache-Control"] == "no-store"

    def test_json_response_none_origin_omits_cors_preflight_keys(self) -> None:
        resp = json_response(503, {"code": "cors_misconfigured"}, None)
        headers = resp["headers"]
        assert "Access-Control-Allow-Origin" not in headers
        assert "Access-Control-Allow-Methods" not in headers
        assert headers["content-type"] == "application/json"
        assert "Content-Security-Policy" in headers

    def test_body_can_be_list(self) -> None:
        resp = json_response(200, [1, 2, 3], "*")
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"]) == [1, 2, 3]
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
        assert "Content-Security-Policy" in resp["headers"]
        assert resp["headers"]["Cache-Control"] == "no-store"

    def test_error_response_shape(self) -> None:
        resp = json_response(400, {"message": "bad", "code": "x"}, "*")
        assert resp["statusCode"] == 400
        assert json.loads(resp["body"]) == {"message": "bad", "code": "x"}
        assert "Cache-Control" in resp["headers"]


class TestOptionsResponse:
    def test_returns_204_with_cors_preflight_headers(self) -> None:
        resp = options_response("https://app.example.com")

        assert resp["statusCode"] == 204
        assert resp["body"] == ""

        headers = resp["headers"]
        assert headers["Access-Control-Allow-Origin"] == "https://app.example.com"
        # Methods string must enumerate every verb the API gateway exposes.
        for verb in ("GET", "POST", "PUT", "DELETE", "OPTIONS"):
            assert verb in headers["Access-Control-Allow-Methods"]
        assert headers["Access-Control-Allow-Headers"] == "Content-Type,Authorization"
        # No content-type header on a no-content response.
        assert "content-type" not in headers
        assert "Content-Security-Policy" in headers
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]

    def test_options_response_none_origin_omits_cors(self) -> None:
        resp = options_response(None)
        assert resp["statusCode"] == 204
        h = resp["headers"]
        assert "Access-Control-Allow-Origin" not in h
        assert "Content-Security-Policy" in h

    def test_echoes_wildcard_origin(self) -> None:
        resp = options_response("*")
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
