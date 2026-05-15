"""Unit tests for ``services.question_banks.controller`` routing and dispatch."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Unauthorized
from services.question_banks.controller import (
    _route_question_banks,
    handle_question_banks_request,
)


class TestRouteQuestionBanks:
    @pytest.mark.parametrize(
        "method,path,action,params",
        [
            (
                "POST",
                "/courses/c1/question-banks",
                "create_question_bank",
                {"courseId": "c1"},
            ),
            (
                "POST",
                "/courses/c1/question-banks/b1/publish",
                "publish_question_bank",
                {"courseId": "c1", "questionBankId": "b1"},
            ),
            (
                "POST",
                "/courses/c1/question-banks/b1/questions",
                "create_draft_question",
                {"courseId": "c1", "questionBankId": "b1"},
            ),
            (
                "OPTIONS",
                "/courses/c1/question-banks/b1/publish",
                "options_question_bank_publish",
                {"courseId": "c1"},
            ),
        ],
    )
    def test_known_routes(
        self, method: str, path: str, action: str, params: Dict[str, str]
    ) -> None:
        got_action, got_params = _route_question_banks(method, path)
        assert got_action == action
        assert got_params == params

    def test_unknown_route(self) -> None:
        action, params = _route_question_banks("GET", "/courses/c1/question-banks/b1")
        assert action == "not_found"
        assert params == {}


def _event(
    *,
    method: str,
    path: str,
    body: Dict[str, Any] | None = None,
    sub: str = "teacher-sub",
) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "requestContext": {
            "http": {"method": method, "path": path},
            "authorizer": {"claims": {"sub": sub, "custom:role": "teacher"}},
        },
        "rawPath": path,
    }
    if body is not None:
        evt["body"] = json.dumps(body)
    return evt


class TestHandleQuestionBanksRequest:
    def test_publish_success(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/question-banks/b1/publish",
                body={"n": 2, "moduleId": "m1"},
            ),
            origin="https://teach.example.com",
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 200
        qb_svc.publish_question_bank.assert_called_once_with(
            "c1", "b1", "m1", 2, cognito_sub="teacher-sub", role="teacher"
        )

    def test_create_draft_question_success(self) -> None:
        qb_svc = MagicMock()
        qb_svc.create_draft_question.return_value = "q-new"
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/question-banks/b1/questions",
                body={
                    "promptText": "What?",
                    "optionsJson": [{"key": "A", "text": "a"}],
                    "correctOptionKey": "A",
                },
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["questionId"] == "q-new"

    def test_unauthenticated_returns_401(self) -> None:
        evt = _event(
            method="POST",
            path="/courses/c1/question-banks/b1/publish",
            body={"n": 1, "moduleId": "m1"},
            sub="",
        )
        resp = handle_question_banks_request(evt, origin=None, qb_svc=MagicMock())
        assert resp is not None
        assert resp["statusCode"] == 401

    def test_bad_request_from_service_mapped(self) -> None:
        qb_svc = MagicMock()
        qb_svc.publish_question_bank.side_effect = BadRequest("bad n")
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/question-banks/b1/publish",
                body={"n": 99, "moduleId": "m1"},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        payload = json.loads(resp["body"])
        assert payload["code"] == "bad_request"
