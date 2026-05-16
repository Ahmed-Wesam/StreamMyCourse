"""HTTP adapter for question banks and module quizzes (QB-B permissions)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.common.errors import BadRequest, HttpError, Unauthorized
from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
)
from services.common.validation import (
    optional_bool,
    optional_str,
    parse_json_body,
    require_int,
    require_json_array_or_object,
    require_str,
    require_string_mapping,
)
from services.question_banks.service import QuestionBankService

logger = logging.getLogger(__name__)


def _api_error_payload(exc: HttpError) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return payload


def _api_error_response(exc: HttpError, origin: Optional[str]) -> Dict[str, Any]:
    return json_response(exc.status_code, _api_error_payload(exc), origin)


def _method_and_path(event: Dict[str, Any]) -> Tuple[str, str]:
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    )
    return method, apigw_routing_path(event)


def _actor_sub(claims: Dict[str, Any]) -> str:
    return str(claims.get("sub", "") or "").strip()


def _actor_role(claims: Dict[str, Any]) -> str:
    return str(claims.get("custom:role") or claims.get("role") or "student").strip().lower()


def _route_question_banks(method: str, path: str) -> Tuple[str, Dict[str, str]]:
    parts = [p for p in path.split("/") if p]
    if (
        method == "GET"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "question-banks"
    ):
        return "list_question_banks", {"courseId": parts[1]}
    if (
        method == "GET"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "module-quizzes"
    ):
        return "list_module_quizzes", {"courseId": parts[1]}
    if (
        method == "GET"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "questions"
    ):
        return "list_question_bank_questions", {
            "courseId": parts[1],
            "questionBankId": parts[3],
        }
    if (
        method == "POST"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "question-banks"
    ):
        return "create_question_bank", {"courseId": parts[1]}
    if (
        method == "POST"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
        and parts[5] == "submit"
    ):
        return "submit_module_quiz", {"courseId": parts[1], "moduleId": parts[3]}
    if (
        method == "POST"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
        and parts[5] == "start"
    ):
        return "start_module_quiz", {"courseId": parts[1], "moduleId": parts[3]}
    if (
        method == "POST"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
    ):
        return "create_module_quiz", {"courseId": parts[1], "moduleId": parts[3]}
    if (
        method == "POST"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "publish"
    ):
        return "publish_question_bank", {
            "courseId": parts[1],
            "questionBankId": parts[3],
        }
    if (
        method == "POST"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "questions"
    ):
        return "create_draft_question", {
            "courseId": parts[1],
            "questionBankId": parts[3],
        }
    if (
        method == "PATCH"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "questions"
    ):
        return "update_question", {
            "courseId": parts[1],
            "questionBankId": parts[3],
            "questionId": parts[5],
        }
    if (
        method == "DELETE"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "questions"
    ):
        return "delete_question", {
            "courseId": parts[1],
            "questionBankId": parts[3],
            "questionId": parts[5],
        }
    if (
        method == "OPTIONS"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "question-banks"
    ):
        return "options_question_bank_collection", {"courseId": parts[1]}
    if (
        method == "OPTIONS"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "module-quizzes"
    ):
        return "options_module_quizzes_collection", {"courseId": parts[1]}
    if (
        method == "OPTIONS"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "publish"
    ):
        return "options_question_bank_publish", {"courseId": parts[1]}
    if (
        method == "OPTIONS"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "questions"
    ):
        return "options_question_bank_questions", {"courseId": parts[1]}
    if (
        method == "OPTIONS"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "question-banks"
        and parts[4] == "questions"
    ):
        return "options_question_bank_question_item", {"courseId": parts[1]}
    if (
        method == "OPTIONS"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
        and parts[5] == "submit"
    ):
        return "options_module_quiz_submit", {"courseId": parts[1], "moduleId": parts[3]}
    if (
        method == "OPTIONS"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
        and parts[5] == "start"
    ):
        return "options_module_quiz_start", {"courseId": parts[1], "moduleId": parts[3]}
    if (
        method == "OPTIONS"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
    ):
        return "options_module_quiz", {"courseId": parts[1], "moduleId": parts[3]}
    return "not_found", {}


def handle_question_banks_request(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    qb_svc: QuestionBankService,
) -> Optional[Dict[str, Any]]:
    """Handle question-bank routes; return ``None`` if this request is not ours."""
    method, raw_path = _method_and_path(event)
    action, params = _route_question_banks(method, raw_path)
    if action == "not_found":
        return None

    if action.startswith("options_"):
        return options_response(origin)

    claims = apigw_cognito_claims(event)
    try:
        if not _actor_sub(claims):
            raise Unauthorized("Authentication required")

        if action == "list_question_banks":
            items = qb_svc.list_question_banks_for_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            return json_response(200, items, origin)

        if action == "list_module_quizzes":
            items = qb_svc.list_module_quizzes_for_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            return json_response(200, items, origin)

        if action == "list_question_bank_questions":
            items = qb_svc.list_questions_for_publisher(
                params["courseId"],
                params["questionBankId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            return json_response(200, items, origin)

        if action == "create_question_bank":
            bank_id = qb_svc.create_question_bank(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            return json_response(201, {"questionBankId": bank_id}, origin)

        if action == "submit_module_quiz":
            body = parse_json_body(event)
            attempt_id = require_str(body, "attemptId")
            answers = require_string_mapping(body, "answers")
            payload = qb_svc.submit_module_quiz(
                params["courseId"],
                params["moduleId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                attempt_id=attempt_id,
                answers=answers,
            )
            return json_response(200, payload, origin)

        if action == "start_module_quiz":
            body = parse_json_body(event)
            retake = optional_bool(body, "retake", default=False)
            payload = qb_svc.start_module_quiz(
                params["courseId"],
                params["moduleId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                retake=retake,
            )
            return json_response(200, payload, origin)

        if action == "create_module_quiz":
            body = parse_json_body(event)
            qbid = require_str(body, "questionBankId")
            quiz_id = qb_svc.create_module_quiz(
                params["courseId"],
                params["moduleId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                question_bank_id=qbid,
            )
            return json_response(201, {"quizId": quiz_id}, origin)

        if action == "publish_question_bank":
            body = parse_json_body(event)
            n = require_int(body, "n")
            module_id = require_str(body, "moduleId")
            qb_svc.publish_question_bank(
                params["courseId"],
                params["questionBankId"],
                module_id,
                n,
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            return json_response(200, {"status": "PUBLISHED"}, origin)

        if action == "create_draft_question":
            body = parse_json_body(event)
            prompt = require_str(body, "promptText")
            opts = require_json_array_or_object(body, "optionsJson")
            correct_raw = optional_str(body, "correctOptionKey", "").strip()
            correct_key = correct_raw or None
            bank = qb_svc.get_bank_for_course(
                params["courseId"],
                params["questionBankId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            if bank.status == "DRAFT":
                qid = qb_svc.create_draft_question(
                    params["courseId"],
                    params["questionBankId"],
                    prompt_text=prompt,
                    options_json=opts,
                    correct_option_key=correct_key,
                    cognito_sub=_actor_sub(claims),
                    role=_actor_role(claims),
                )
            elif bank.status == "PUBLISHED":
                if not correct_key:
                    raise BadRequest("correctOptionKey must not be empty")
                qid = qb_svc.add_published_question(
                    params["courseId"],
                    params["questionBankId"],
                    prompt_text=prompt,
                    options_json=opts,
                    correct_option_key=correct_key,
                    cognito_sub=_actor_sub(claims),
                    role=_actor_role(claims),
                )
            else:
                raise BadRequest("Question bank cannot accept questions in this status")
            return json_response(201, {"questionId": qid}, origin)

        if action == "update_question":
            body = parse_json_body(event)
            if (
                "promptText" not in body
                and "optionsJson" not in body
                and "correctOptionKey" not in body
            ):
                raise BadRequest(
                    "At least one of promptText, optionsJson, correctOptionKey is required"
                )
            prompt_patch = None
            if "promptText" in body:
                prompt_patch = require_str(body, "promptText")
            opts_patch = None
            if "optionsJson" in body:
                opts_patch = require_json_array_or_object(body, "optionsJson")
            correct_patch = None
            if "correctOptionKey" in body:
                ck = optional_str(body, "correctOptionKey", "")
                if not ck.strip():
                    raise BadRequest("correctOptionKey must not be empty")
                correct_patch = ck.strip()
            qb_svc.update_question(
                params["courseId"],
                params["questionBankId"],
                params["questionId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                prompt_text=prompt_patch,
                options_json=opts_patch,
                correct_option_key=correct_patch,
            )
            return json_response(200, {"status": "updated"}, origin)

        if action == "delete_question":
            qb_svc.delete_question(
                params["courseId"],
                params["questionBankId"],
                params["questionId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            return json_response(200, {"status": "deleted"}, origin)

        return None
    except HttpError as exc:
        logger.info(
            "question_banks_http_error",
            extra={
                "status": exc.status_code,
                "code": exc.code,
                "path": raw_path,
            },
        )
        return _api_error_response(exc, origin)
