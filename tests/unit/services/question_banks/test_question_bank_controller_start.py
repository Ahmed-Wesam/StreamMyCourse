"""Unit tests for POST .../modules/{moduleId}/quiz/start (QB-F slice 4)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.common.errors import NotFound
from services.question_banks.controller import (
    _route_question_banks,
    handle_question_banks_request,
)


def _event(
    *,
    method: str,
    path: str,
    sub: str = "student-sub",
    role: str = "student",
) -> Dict[str, Any]:
    return {
        "requestContext": {
            "http": {"method": method, "path": path},
            "authorizer": {"claims": {"sub": sub, "custom:role": role}},
        },
        "rawPath": path,
    }


class TestRouteQuizStart:
    def test_quiz_start_matches_before_create_module_quiz(self) -> None:
        action, params = _route_question_banks(
            "POST", "/courses/c1/modules/m1/quiz/start"
        )
        assert action == "start_module_quiz"
        assert params == {"courseId": "c1", "moduleId": "m1"}

    def test_create_module_quiz_still_matches_quiz_only_path(self) -> None:
        action, params = _route_question_banks(
            "POST", "/courses/c1/modules/m1/quiz"
        )
        assert action == "create_module_quiz"
        assert params == {"courseId": "c1", "moduleId": "m1"}

    def test_options_quiz_start(self) -> None:
        action, params = _route_question_banks(
            "OPTIONS", "/courses/c1/modules/m1/quiz/start"
        )
        assert action == "options_module_quiz_start"
        assert params == {"courseId": "c1", "moduleId": "m1"}


class TestHandleStartModuleQuiz:
    def test_post_routes_to_start_and_returns_200(self) -> None:
        qb_svc = MagicMock()
        qb_svc.start_module_quiz.return_value = {
            "moduleQuizId": "mq1",
            "moduleId": "m1",
            "servedCountN": 2,
            "questions": [
                {
                    "id": "q1",
                    "promptText": "What?",
                    "optionsJson": [{"key": "A", "text": "a"}],
                }
            ],
        }
        resp = handle_question_banks_request(
            _event(method="POST", path="/courses/c1/modules/m1/quiz/start"),
            origin="https://student.example.com",
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["moduleQuizId"] == "mq1"
        assert len(body["questions"]) == 1
        qb_svc.start_module_quiz.assert_called_once_with(
            "c1", "m1", cognito_sub="student-sub", role="student"
        )

    def test_not_found_from_service_returns_404(self) -> None:
        qb_svc = MagicMock()
        qb_svc.start_module_quiz.side_effect = NotFound("Module quiz not available")
        resp = handle_question_banks_request(
            _event(method="POST", path="/courses/c1/modules/m1/quiz/start"),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 404
        payload = json.loads(resp["body"])
        assert payload["code"] == "not_found"
