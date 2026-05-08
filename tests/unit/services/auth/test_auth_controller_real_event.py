"""Unit tests for auth controller with real API Gateway event structures.

Tests the actual apigw_cognito_claims path without monkeypatching _claims_dict.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.auth.controller import handle_users_me
class TestHandleUsersMeRealEventStructure:
    """Tests using real API Gateway v2 event structures (no _claims_dict mocking)."""

    def _make_api_gateway_v2_event(
        self,
        *,
        sub: str = "user-123",
        email: str = "user@example.com",
        role: str = "student",
        include_authorizer: bool = True,
    ) -> Dict[str, Any]:
        """Build a realistic API Gateway v2 HTTP API event."""
        event: Dict[str, Any] = {
            "version": "2.0",
            "routeKey": "GET /users/me",
            "rawPath": "/users/me",
            "rawQueryString": "",
            "headers": {
                "accept": "application/json",
                "host": "api.example.com",
            },
            "requestContext": {
                "domainName": "api.example.com",
                "domainPrefix": "api",
                "http": {"method": "GET", "path": "/users/me", "protocol": "HTTP/1.1", "sourceIp": "1.2.3.4"},
                "requestId": "test-request-id",
                "routeKey": "GET /users/me",
                "stage": "prod",
                "time": "05/May/2026:19:57:00 +0000",
                "timeEpoch": 1750000000000,
            },
        }

        if include_authorizer:
            # API Gateway v2 HTTP API structure: claims directly in authorizer.claims
            event["requestContext"]["authorizer"] = {
                "claims": {
                    "sub": sub,
                    "email": email,
                    "custom:role": role,
                    "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123",
                },
            }

        return event

    def test_real_event_with_authorizer_jwt_claims(self) -> None:
        """Test with real API Gateway v2 authorizer.jwt.claims structure."""
        event = self._make_api_gateway_v2_event(
            sub="user-456",
            email="real@example.com",
            role="teacher",
        )
        auth_svc = MagicMock()
        auth_svc.get_or_create_profile.return_value = {"userId": "user-456"}

        resp = handle_users_me(
            event,
            origin="*",
            auth_svc=auth_svc,
        )

        assert resp["statusCode"] == 200
        auth_svc.get_or_create_profile.assert_called_once_with(
            user_sub="user-456",
            email="real@example.com",
            role="teacher",
        )

    def test_real_event_without_authorizer_returns_401(self) -> None:
        """Test that missing authorizer returns 401."""
        event = self._make_api_gateway_v2_event(include_authorizer=False)
        auth_svc = MagicMock()

        resp = handle_users_me(
            event,
            origin="*",
            auth_svc=auth_svc,
        )

        assert resp["statusCode"] == 401
        auth_svc.get_or_create_profile.assert_not_called()

    def test_real_event_with_authorizer_flat_claims(self) -> None:
        """Test with API Gateway v1-style flat claims in authorizer."""
        event = self._make_api_gateway_v2_event()
        # Replace with v1-style flat claims
        event["requestContext"]["authorizer"] = {
            "sub": "user-789",
            "email": "flat@example.com",
            "custom:role": "admin",
            "principalId": "user-789",
        }

        auth_svc = MagicMock()
        auth_svc.get_or_create_profile.return_value = {"userId": "user-789"}

        resp = handle_users_me(
            event,
            origin="*",
            auth_svc=auth_svc,
        )

        assert resp["statusCode"] == 200
        auth_svc.get_or_create_profile.assert_called_once_with(
            user_sub="user-789",
            email="flat@example.com",
            role="admin",
        )

    def test_real_event_with_stringified_claims(self) -> None:
        """Test with stringified JSON claims (some Lambda@Edge configurations)."""
        event = self._make_api_gateway_v2_event()
        claims_json = json.dumps({
            "sub": "user-string",
            "email": "stringified@example.com",
            "custom:role": "student",
        })
        event["requestContext"]["authorizer"] = {"claims": claims_json}

        auth_svc = MagicMock()
        auth_svc.get_or_create_profile.return_value = {"userId": "user-string"}

        resp = handle_users_me(
            event,
            origin="*",
            auth_svc=auth_svc,
        )

        assert resp["statusCode"] == 200
        auth_svc.get_or_create_profile.assert_called_once_with(
            user_sub="user-string",
            email="stringified@example.com",
            role="student",
        )

    def test_real_event_with_authorization_header_but_no_authorizer_returns_401(self) -> None:
        """Defense-in-depth: Authorization headers are ignored; only authorizer context is trusted."""
        event = self._make_api_gateway_v2_event(include_authorizer=False)
        event["headers"]["Authorization"] = "Bearer fake.token.here"
        auth_svc = MagicMock()

        resp = handle_users_me(event, origin="*", auth_svc=auth_svc)

        assert resp["statusCode"] == 401
        auth_svc.get_or_create_profile.assert_not_called()

    def test_real_event_missing_sub_in_claims_returns_401(self) -> None:
        """Test that claims without sub field returns 401."""
        event = self._make_api_gateway_v2_event()
        # Claims without sub (direct claims structure)
        event["requestContext"]["authorizer"] = {
            "claims": {
                "email": "no-sub@example.com",
                "custom:role": "student",
            }
        }

        auth_svc = MagicMock()

        resp = handle_users_me(
            event,
            origin="*",
            auth_svc=auth_svc,
        )

        assert resp["statusCode"] == 401
        auth_svc.get_or_create_profile.assert_not_called()

    def test_real_event_empty_sub_returns_401(self) -> None:
        """Test that empty sub field returns 401."""
        event = self._make_api_gateway_v2_event()
        event["requestContext"]["authorizer"] = {
            "claims": {
                "sub": "   ",  # Whitespace only
                "email": "empty-sub@example.com",
            }
        }

        auth_svc = MagicMock()

        resp = handle_users_me(
            event,
            origin="*",
            auth_svc=auth_svc,
        )

        assert resp["statusCode"] == 401
        auth_svc.get_or_create_profile.assert_not_called()
