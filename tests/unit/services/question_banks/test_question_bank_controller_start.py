"""Unit tests for POST .../modules/{moduleId}/quiz/start (QB-F slice 4)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

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
    def test_quiz_submit_matches_before_start_before_create_module_quiz(self) -> None:
        action_submit, _ = _route_question_banks(
            "POST", "/courses/c1/modules/m1/quiz/submit"
        )
        assert action_submit == "submit_module_quiz"

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
            "phase": "in_progress",
            "moduleQuizId": "mq1",
            "moduleId": "m1",
            "servedCountN": 2,
            "attemptId": "att-1",
            "attemptNumber": 1,
            "questionIds": ["q1"],
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
        assert body["attemptId"] == "att-1"
        assert body["attemptNumber"] == 1
        assert body["questionIds"] == ["q1"]
        assert [q["id"] for q in body["questions"]] == body["questionIds"]
        assert len(body["questions"]) == 1
        qb_svc.start_module_quiz.assert_called_once_with(
            "c1", "m1", cognito_sub="student-sub", role="student", retake=False
        )

    def test_optional_retake_true_passed_to_service(self) -> None:
        qb_svc = MagicMock()
        qb_svc.start_module_quiz.return_value = {"phase": "in_progress"}
        evt = {
            "requestContext": {
                "http": {
                    "method": "POST",
                    "path": "/courses/c1/modules/m1/quiz/start",
                },
                "authorizer": {"claims": {"sub": "student-sub", "custom:role": "student"}},
            },
            "rawPath": "/courses/c1/modules/m1/quiz/start",
            "body": '{"retake": true}',
        }
        resp = handle_question_banks_request(
            evt, origin=None, qb_svc=qb_svc
        )
        assert resp is not None
        assert resp["statusCode"] == 200
        qb_svc.start_module_quiz.assert_called_once_with(
            "c1", "m1", cognito_sub="student-sub", role="student", retake=True
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
