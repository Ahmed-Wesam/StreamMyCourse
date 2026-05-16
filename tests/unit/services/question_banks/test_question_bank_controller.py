"""Unit tests for ``services.question_banks.controller`` routing and dispatch."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Conflict
from services.question_banks.controller import (
    _route_question_banks,
    handle_question_banks_request,
)
from services.question_banks.models import QuestionBank


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
                "PATCH",
                "/courses/c1/question-banks/b1",
                "rename_question_bank",
                {"courseId": "c1", "questionBankId": "b1"},
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
                "PATCH",
                "/courses/c1/question-banks/b1/questions/q1",
                "update_question",
                {"courseId": "c1", "questionBankId": "b1", "questionId": "q1"},
            ),
            (
                "DELETE",
                "/courses/c1/question-banks/b1/questions/q1",
                "delete_question",
                {"courseId": "c1", "questionBankId": "b1", "questionId": "q1"},
            ),
            (
                "OPTIONS",
                "/courses/c1/question-banks/b1",
                "options_question_bank_item",
                {"courseId": "c1"},
            ),
            (
                "OPTIONS",
                "/courses/c1/question-banks/b1/questions/q1",
                "options_question_bank_question_item",
                {"courseId": "c1"},
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
    def test_create_question_bank_success_with_name(self) -> None:
        qb_svc = MagicMock()
        qb_svc.create_question_bank.return_value = {
            "questionBankId": "bank-new",
            "name": "Final exam bank",
        }
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/question-banks",
                body={"name": " Final exam bank "},
            ),
            origin="https://teach.example.com",
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 201
        assert json.loads(resp["body"]) == {
            "questionBankId": "bank-new",
            "name": "Final exam bank",
        }
        qb_svc.create_question_bank.assert_called_once_with(
            "c1",
            name="Final exam bank",
            cognito_sub="teacher-sub",
            role="teacher",
        )

    def test_create_question_bank_missing_name_returns_400(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(method="POST", path="/courses/c1/question-banks", body={}),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        qb_svc.create_question_bank.assert_not_called()

    def test_rename_question_bank_success(self) -> None:
        qb_svc = MagicMock()
        qb_svc.rename_question_bank.return_value = {
            "questionBankId": "b1",
            "name": "Renamed bank",
        }
        resp = handle_question_banks_request(
            _event(
                method="PATCH",
                path="/courses/c1/question-banks/b1",
                body={"name": " Renamed bank "},
            ),
            origin="https://teach.example.com",
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"]) == {
            "questionBankId": "b1",
            "name": "Renamed bank",
        }
        qb_svc.rename_question_bank.assert_called_once_with(
            "c1",
            "b1",
            name="Renamed bank",
            cognito_sub="teacher-sub",
            role="teacher",
        )

    def test_rename_question_bank_missing_name_returns_400(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(
                method="PATCH",
                path="/courses/c1/question-banks/b1",
                body={},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        qb_svc.rename_question_bank.assert_not_called()

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
        qb_svc.get_bank_for_course.return_value = QuestionBank(
            id="b1",
            courseId="c1",
            name="Draft bank",
            status="DRAFT",
            createdAt="",
            updatedAt="",
        )
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
        qb_svc.get_bank_for_course.assert_called_once_with(
            "c1", "b1", cognito_sub="teacher-sub", role="teacher"
        )

    def test_post_question_on_published_bank_calls_add_published(self) -> None:
        qb_svc = MagicMock()
        qb_svc.get_bank_for_course.return_value = QuestionBank(
            id="b1",
            courseId="c1",
            name="Published bank",
            status="PUBLISHED",
            createdAt="",
            updatedAt="",
        )
        qb_svc.add_published_question.return_value = "q-pub"
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/question-banks/b1/questions",
                body={
                    "promptText": "Published Q?",
                    "optionsJson": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}],
                    "correctOptionKey": "B",
                },
            ),
            origin="https://teach.example.com",
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["questionId"] == "q-pub"
        qb_svc.add_published_question.assert_called_once_with(
            "c1",
            "b1",
            prompt_text="Published Q?",
            options_json=[{"key": "A", "text": "a"}, {"key": "B", "text": "b"}],
            correct_option_key="B",
            cognito_sub="teacher-sub",
            role="teacher",
        )
        qb_svc.create_draft_question.assert_not_called()

    def test_post_question_on_published_bank_missing_correct_returns_400(self) -> None:
        qb_svc = MagicMock()
        qb_svc.get_bank_for_course.return_value = QuestionBank(
            id="b1",
            courseId="c1",
            name="Published bank",
            status="PUBLISHED",
            createdAt="",
            updatedAt="",
        )
        resp = handle_question_banks_request(
            _event(
                method="POST",
                path="/courses/c1/question-banks/b1/questions",
                body={
                    "promptText": "No key",
                    "optionsJson": [{"key": "A", "text": "a"}],
                },
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        payload = json.loads(resp["body"])
        assert payload["code"] == "bad_request"
        qb_svc.add_published_question.assert_not_called()

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

    def test_patch_question_success(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(
                method="PATCH",
                path="/courses/c1/question-banks/b1/questions/q9",
                body={"promptText": "Updated?"},
            ),
            origin="https://teach.example.com",
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["status"] == "updated"
        qb_svc.update_question.assert_called_once_with(
            "c1",
            "b1",
            "q9",
            cognito_sub="teacher-sub",
            role="teacher",
            prompt_text="Updated?",
            options_json=None,
            correct_option_key=None,
        )

    def test_delete_question_success(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(method="DELETE", path="/courses/c1/question-banks/b1/questions/q9"),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["status"] == "deleted"
        qb_svc.delete_question.assert_called_once_with(
            "c1",
            "b1",
            "q9",
            cognito_sub="teacher-sub",
            role="teacher",
        )

    def test_patch_question_empty_body_returns_400(self) -> None:
        qb_svc = MagicMock()
        resp = handle_question_banks_request(
            _event(
                method="PATCH",
                path="/courses/c1/question-banks/b1/questions/q9",
                body={},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 400
        payload = json.loads(resp["body"])
        assert payload["code"] == "bad_request"
        qb_svc.update_question.assert_not_called()

    def test_patch_question_conflict_returns_409(self) -> None:
        qb_svc = MagicMock()
        qb_svc.update_question.side_effect = Conflict("Published questions cannot be updated")
        resp = handle_question_banks_request(
            _event(
                method="PATCH",
                path="/courses/c1/question-banks/b1/questions/q9",
                body={"promptText": "x"},
            ),
            origin=None,
            qb_svc=qb_svc,
        )
        assert resp is not None
        assert resp["statusCode"] == 409
        payload = json.loads(resp["body"])
        assert payload["code"] == "conflict"
