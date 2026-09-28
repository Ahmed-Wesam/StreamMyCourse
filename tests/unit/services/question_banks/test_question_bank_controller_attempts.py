"""Unit tests for GET .../modules/{moduleId}/quiz/attempts (RS-8 slice 4)."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

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


class TestRouteQuizAttempts:
    def test_get_attempts_route(self) -> None:
        action, params = _route_question_banks(
            "GET", "/courses/c1/modules/m1/quiz/attempts"
        )
        assert action == "list_module_quiz_attempts"
        assert params == {"courseId": "c1", "moduleId": "m1"}

    def test_options_attempts_route(self) -> None:
        action, _ = _route_question_banks(
            "OPTIONS", "/courses/c1/modules/m1/quiz/attempts"
        )
        assert action == "options_module_quiz_attempts"


def test_handle_list_module_quiz_attempts_returns_json_array() -> None:
    qb_svc = MagicMock()
    qb_svc.list_module_quiz_attempts.return_value = [
        {"attemptId": "a1", "attemptNumber": 1, "passed": False}
    ]
    resp = handle_question_banks_request(
        _event(method="GET", path="/courses/c1/modules/m1/quiz/attempts"),
        origin="https://app.example.com",
        qb_svc=qb_svc,
    )
    assert resp is not None
    assert resp["statusCode"] == 200
    qb_svc.list_module_quiz_attempts.assert_called_once_with(
        "c1",
        "m1",
        cognito_sub="student-sub",
        role="student",
    )
