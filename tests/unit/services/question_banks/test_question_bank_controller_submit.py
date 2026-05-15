"""Unit tests for POST .../modules/{moduleId}/quiz/submit (QB-H slice 4)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

from services.common.errors import Conflict, NotFound
from services.question_banks.controller import (
    _route_question_banks,
    handle_question_banks_request,
)


def _event(
    *,
    method: str,
    path: str,
    body: Dict[str, Any] | None = None,
    sub: str = "student-sub",
    role: str = "student",
) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "requestContext": {
            "http": {"method": method, "path": path},
            "authorizer": {"claims": {"sub": sub, "custom:role": role}},
        },
        "rawPath": path,
    }
    if body is not None:
        evt["body"] = json.dumps(body)
    return evt


class TestRouteQuizSubmit:
    def test_quiz_submit_matches_before_start_before_create(self) -> None:
        a_submit, p_submit = _route_question_banks(
            "POST", "/courses/c1/modules/m1/quiz/submit"
        )
        assert a_submit == "submit_module_quiz"
        assert p_submit == {"courseId": "c1", "moduleId": "m1"}

        a_start, p_start = _route_question_banks(
            "POST", "/courses/c1/modules/m1/quiz/start"
        )
        assert a_start == "start_module_quiz"
        assert p_start == {"courseId": "c1", "moduleId": "m1"}

        a_create, p_create = _route_question_banks(
            "POST", "/courses/c1/modules/m1/quiz"
        )
        assert a_create == "create_module_quiz"
        assert p_create == {"courseId": "c1", "moduleId": "m1"}

    def test_options_quiz_submit(self) -> None:
        action, params = _route_question_banks(
            "OPTIONS", "/courses/c1/modules/m1/quiz/submit"
        )
        assert action == "options_module_quiz_submit"
        assert params == {"courseId": "c1", "moduleId": "m1"}


class TestHandleSubmitModuleQuiz:
    def test_post_submit_returns_200(self) -> None:
        qb_svc = MagicMock()
        qb_svc.submit_module_quiz.return_value = {
            "attemptId": "att-1",
            "attemptNumber": 1,
            "correctCount": 1,
            "totalCount": 1,
            "questions": [
                {
                    "id": "q1",
                    "promptText": "What?",
                    "selectedOptionKey": "A",
                    "correctOptionKey": "A",
                    "isCorrect": True,
                }
            ],
        }
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/modules/m1/quiz/submit",
                body={"attemptId": "att-1", "answers": {"q1": "A"}},
            ),
            origin="https://student.example.com",
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["attemptId"] == "att-1"
        assert body["correctCount"] == 1
        assert body["totalCount"] == 1
        qb_svc.submit_module_quiz.assert_called_once_with(
            "c1",
            "m1",
            cognito_sub="student-sub",
            role="student",
            attempt_id="att-1",
            answers={"q1": "A"},
        )

    def test_missing_attempt_id_returns_400(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/modules/m1/quiz/submit",
                body={"answers": {"q1": "A"}},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        payload = json.loads(resp["body"])
        assert payload["code"] == "bad_request"
        qb_svc.submit_module_quiz.assert_not_called()

    def test_invalid_answers_type_returns_400(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/modules/m1/quiz/submit",
                body={"attemptId": "att-1", "answers": "nope"},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        payload = json.loads(resp["body"])
        assert payload["code"] == "bad_request"
        qb_svc.submit_module_quiz.assert_not_called()

    def test_not_found_from_service_returns_404(self) -> None:
        qb_svc = MagicMock()
        qb_svc.submit_module_quiz.side_effect = NotFound(
            "Module quiz attempt not found"
        )
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/modules/m1/quiz/submit",
                body={"attemptId": "unknown", "answers": {"q1": "A"}},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 404
        payload = json.loads(resp["body"])
        assert payload["code"] == "not_found"

    def test_conflict_from_service_returns_409(self) -> None:
        qb_svc = MagicMock()
        qb_svc.submit_module_quiz.side_effect = Conflict("Quiz attempt already submitted")
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/modules/m1/quiz/submit",
                body={"attemptId": "att-1", "answers": {"q1": "A"}},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 409
        payload = json.loads(resp["body"])
        assert payload["code"] == "conflict"
