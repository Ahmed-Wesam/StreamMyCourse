"""HTTP adapter for question banks and module quizzes (QB-B permissions)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.common.errors import HttpError, Unauthorized
from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
)
from services.common.validation import optional_str, parse_json_body
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
        method == "POST"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "question-banks"
    ):
        return "create_question_bank", {"courseId": parts[1]}
    if (
        method == "POST"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
    ):
        return "create_module_quiz", {"courseId": parts[1], "moduleId": parts[3]}
    if (
        method == "OPTIONS"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "question-banks"
    ):
        return "options_question_bank_collection", {"courseId": parts[1]}
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

        if action == "create_question_bank":
            bank_id = qb_svc.create_question_bank(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
            )
            return json_response(201, {"questionBankId": bank_id}, origin)

        if action == "create_module_quiz":
            body = parse_json_body(event)
            qbid = optional_str(body, "questionBankId", "").strip() or None
            quiz_id = qb_svc.create_module_quiz(
                params["courseId"],
                params["moduleId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                question_bank_id=qbid,
            )
            return json_response(201, {"quizId": quiz_id}, origin)

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
