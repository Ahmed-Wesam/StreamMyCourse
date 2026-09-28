"""Unit tests for POST /contact HTTP controller."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, ServiceUnavailable


@pytest.fixture
def controller_module():
    from services.contact import controller

    return controller


@pytest.fixture
def contact_svc() -> MagicMock:
    return MagicMock()


def _valid_body() -> Dict[str, str]:
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "category": "Technical Issue",
        "subject": "Video playback",
        "message": "The player stops after 10 seconds.",
    }


class TestRouting:
    def test_non_contact_route_returns_none(
        self, controller_module, contact_svc: MagicMock, make_lambda_event
    ) -> None:
        evt = make_lambda_event(method="GET", path="/courses")
        assert (
            controller_module.handle_contact_request(evt, origin="https://app.test", contact_svc=contact_svc)
            is None
        )
        contact_svc.submit_from_dict.assert_not_called()

    def test_options_contact_returns_cors(
        self, controller_module, contact_svc: MagicMock, make_lambda_event
    ) -> None:
        evt = make_lambda_event(method="OPTIONS", path="/contact")
        resp = controller_module.handle_contact_request(
            evt, origin="https://app.test", contact_svc=contact_svc
        )
        assert resp is not None
        assert resp["statusCode"] == 204


class TestPostContact:
    def test_success_returns_202(
        self, controller_module, contact_svc: MagicMock, make_lambda_event
    ) -> None:
        evt = make_lambda_event(method="POST", path="/contact", body=_valid_body())
        resp = controller_module.handle_contact_request(
            evt, origin="https://app.test", contact_svc=contact_svc
        )
        assert resp is not None
        assert resp["statusCode"] == 202
        contact_svc.submit_from_dict.assert_called_once()

    def test_honeypot_returns_202_without_service_error(
        self, controller_module, contact_svc: MagicMock, make_lambda_event
    ) -> None:
        body = _valid_body()
        body["rs_hp"] = "spam"
        evt = make_lambda_event(method="POST", path="/contact", body=body)
        resp = controller_module.handle_contact_request(
            evt, origin="https://app.test", contact_svc=contact_svc
        )
        assert resp is not None
        assert resp["statusCode"] == 202

    def test_validation_error_returns_400(
        self, controller_module, contact_svc: MagicMock, make_lambda_event
    ) -> None:
        contact_svc.submit_from_dict.side_effect = BadRequest("bad field")
        evt = make_lambda_event(method="POST", path="/contact", body=_valid_body())
        resp = controller_module.handle_contact_request(
            evt, origin="https://app.test", contact_svc=contact_svc
        )
        assert resp is not None
        assert resp["statusCode"] == 400

    def test_service_unavailable_returns_503(
        self, controller_module, contact_svc: MagicMock, make_lambda_event
    ) -> None:
        contact_svc.submit_from_dict.side_effect = ServiceUnavailable("queue missing")
        evt = make_lambda_event(method="POST", path="/contact", body=_valid_body())
        resp = controller_module.handle_contact_request(
            evt, origin="https://app.test", contact_svc=contact_svc
        )
        assert resp is not None
        assert resp["statusCode"] == 503

    def test_body_over_16kb_returns_400(
        self, controller_module, contact_svc: MagicMock, make_lambda_event
    ) -> None:
        huge = json.dumps({"message": "x" * (16 * 1024)})
        evt = make_lambda_event(method="POST", path="/contact", body=huge)
        resp = controller_module.handle_contact_request(
            evt, origin="https://app.test", contact_svc=contact_svc
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        contact_svc.submit_from_dict.assert_not_called()
