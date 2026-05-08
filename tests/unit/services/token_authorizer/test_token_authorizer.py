from __future__ import annotations

import base64
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[4]
_AUTHZ_INDEX = _REPO_ROOT / "infrastructure" / "lambda" / "catalog_token_authorizer" / "index.py"
_SPEC = importlib.util.spec_from_file_location("catalog_token_authorizer_index", _AUTHZ_INDEX)
assert _SPEC is not None and _SPEC.loader is not None
authorizer = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = authorizer
_SPEC.loader.exec_module(authorizer)


def _b64url(obj: dict) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(obj).encode("utf-8"))
        .decode("utf-8")
        .rstrip("=")
    )


def _make_token(payload: dict, *, kid: str = "kid-1") -> str:
    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    return f"{_b64url(header)}.{_b64url(payload)}.sig"


def _invoke(token: str | None, *, method_arn: str = "arn:aws:execute-api:us-east-1:1:api/stage/GET/x"):
    event = {"methodArn": method_arn}
    if token is not None:
        event["authorizationToken"] = token
    return authorizer.handler(event, None)


def _assert_allow(resp: dict):
    assert resp["policyDocument"]["Statement"][0]["Effect"] == "Allow"
    assert resp["policyDocument"]["Statement"][0]["Action"] == "execute-api:Invoke"
    assert "context" in resp
    assert all(isinstance(v, str) for v in resp["context"].values())


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv(
        "COGNITO_USER_POOL_ARN",
        "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_ABC123DEF",
    )
    monkeypatch.setenv("COGNITO_CLIENT_ID", "client-a,client-b")
    monkeypatch.delenv("FALLBACK_ROLE", raising=False)
    yield


def test_missing_authorization_header_allow_empty_context(env):
    resp = _invoke(None)
    _assert_allow(resp)
    assert resp["context"] == {"sub": "", "role": "", "email": ""}


def test_malformed_token_allow_empty_context(env):
    resp = _invoke("Bearer not-a-jwt")
    _assert_allow(resp)
    assert resp["context"] == {"sub": "", "role": "", "email": ""}


@patch.object(authorizer, "_fetch_jwks")
def test_valid_token_allow_populated_context(mock_fetch, env):
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }

    payload = {
        "sub": "user-123",
        "email": "u@example.com",
        "custom:role": "teacher",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123DEF",
        "aud": "client-a",
        "exp": 9999999999,
        "token_use": "id",
    }
    token = _make_token(payload)

    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp = _invoke(f"Bearer {token}")

    _assert_allow(resp)
    assert resp["principalId"] == "user-123"
    assert resp["context"]["sub"] == "user-123"
    assert resp["context"]["email"] == "u@example.com"
    assert resp["context"]["role"] == "teacher"


@patch.object(authorizer, "_fetch_jwks")
def test_token_use_not_id_allow_empty_context(mock_fetch, env):
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }
    payload = {
        "sub": "user-123",
        "email": "u@example.com",
        "custom:role": "teacher",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123DEF",
        "aud": "client-a",
        "exp": 9999999999,
        "token_use": "access",
    }
    token = _make_token(payload)
    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp = _invoke(f"Bearer {token}")

    _assert_allow(resp)
    assert resp["context"] == {"sub": "", "role": "", "email": ""}


@patch.object(authorizer, "_fetch_jwks")
def test_aud_not_in_allowlist_allow_empty_context(mock_fetch, env, monkeypatch):
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }
    monkeypatch.setenv("COGNITO_CLIENT_ID", "client-a")
    payload = {
        "sub": "user-123",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123DEF",
        "aud": "client-b",
        "exp": 9999999999,
        "token_use": "id",
    }
    token = _make_token(payload)
    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp = _invoke(token)

    _assert_allow(resp)
    assert resp["context"] == {"sub": "", "role": "", "email": ""}


@patch.object(authorizer, "_fetch_jwks")
def test_iss_mismatch_allow_empty_context(mock_fetch, env):
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }
    payload = {
        "sub": "user-123",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/OTHER_POOL",
        "aud": "client-a",
        "exp": 9999999999,
        "token_use": "id",
    }
    token = _make_token(payload)
    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp = _invoke(token)

    _assert_allow(resp)
    assert resp["context"] == {"sub": "", "role": "", "email": ""}


@patch.object(authorizer, "_fetch_jwks")
def test_expired_exp_allow_empty_context(mock_fetch, env):
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }
    payload = {
        "sub": "user-123",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123DEF",
        "aud": "client-a",
        "exp": 10,
        "token_use": "id",
    }
    token = _make_token(payload)
    with patch.object(authorizer, "_verify_signature", return_value=True):
        with patch.object(authorizer.time, "time", return_value=1000.0):
            resp = _invoke(token)

    _assert_allow(resp)
    assert resp["context"] == {"sub": "", "role": "", "email": ""}


@patch.object(authorizer, "_fetch_jwks")
def test_role_extraction_precedence_custom_role_over_fallback(mock_fetch, env, monkeypatch):
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }
    monkeypatch.setenv("FALLBACK_ROLE", "student")
    payload = {
        "sub": "user-123",
        "email": "u@example.com",
        "custom:role": "teacher",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123DEF",
        "aud": "client-a",
        "exp": 9999999999,
        "token_use": "id",
    }
    token = _make_token(payload)
    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp = _invoke(token)
    assert resp["context"]["role"] == "teacher"


def test_wildcard_resource_arn_covers_all_routes(env):
    """The policy Resource must wildcard after the API ID so a cached policy works for all routes."""
    arn = "arn:aws:execute-api:us-east-1:123456789012:abc123def/prod/GET/courses"
    resp = _invoke(None, method_arn=arn)
    resource = resp["policyDocument"]["Statement"][0]["Resource"]
    assert resource == "arn:aws:execute-api:us-east-1:123456789012:abc123def/*"


@patch.object(authorizer, "_fetch_jwks")
def test_authenticated_response_uses_wildcard_resource(mock_fetch, env):
    """Even for a valid authenticated user the Resource must be wildcarded."""
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }
    payload = {
        "sub": "user-123",
        "email": "u@example.com",
        "custom:role": "teacher",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123DEF",
        "aud": "client-a",
        "exp": 9999999999,
        "token_use": "id",
    }
    token = _make_token(payload)
    method_arn = "arn:aws:execute-api:eu-west-1:111:myapi/dev/POST/courses"
    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp = _invoke(f"Bearer {token}", method_arn=method_arn)
    assert resp["policyDocument"]["Statement"][0]["Resource"] == "arn:aws:execute-api:eu-west-1:111:myapi/*"


@patch.object(authorizer, "_fetch_jwks")
def test_role_fallback_then_default_student(mock_fetch, env, monkeypatch):
    mock_fetch.return_value = {
        "keys": [{"kid": "kid-1", "kty": "RSA", "n": "x", "e": "AQAB"}]
    }

    # No custom:role => fallback role
    monkeypatch.setenv("FALLBACK_ROLE", "staff")
    payload = {
        "sub": "user-123",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123DEF",
        "aud": "client-a",
        "exp": 9999999999,
        "token_use": "id",
    }
    token = _make_token(payload)
    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp = _invoke(token)
    assert resp["context"]["role"] == "staff"

    # Empty fallback => default student
    monkeypatch.setenv("FALLBACK_ROLE", "   ")
    with patch.object(authorizer, "_verify_signature", return_value=True):
        resp2 = _invoke(token)
    assert resp2["context"]["role"] == "student"

