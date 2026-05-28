"""Catalog Lambda invoke for video provider edge orchestration."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

_INTERNAL_PREPARE = "video.prepare_upload"
_INTERNAL_COMMIT = "video.commit_pending_upload"
_INTERNAL_PREPARE_MARK_READY = "video.prepare_mark_ready"
_INTERNAL_APPLY_MARK_READY = "video.apply_mark_ready"
_INTERNAL_WEBHOOK_STATUS = "video.webhook_status"
_EDGE_SYSTEM_USER_SUB = "video-provider-edge"

class CatalogInvokeError(Exception):
    """Catalog invoke failed or is not configured."""


class CatalogInvokeHttpError(CatalogInvokeError):
    """Catalog domain rejected the internal invoke with an HTTP-shaped error."""

    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _invoke_catalog_internal(
    *,
    internal: str,
    user_sub: str,
    catalog_lambda_arn: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "internal": internal,
        "userSub": user_sub,
    }
    if extra:
        payload.update(extra)
    client = boto3.client("lambda")
    try:
        response = client.invoke(
            FunctionName=catalog_lambda_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception(
            "catalog_invoke_failed user_sub=%s internal=%s",
            user_sub,
            internal,
        )
        raise CatalogInvokeError("catalog invoke failed") from exc

    status = response.get("StatusCode")
    if status != 200:
        raise CatalogInvokeError(f"catalog invoke status {status!r}")

    function_error = response.get("FunctionError")
    if function_error:
        logger.error(
            "catalog_invoke_function_error user_sub=%s internal=%s error=%s",
            user_sub,
            internal,
            function_error,
        )
        raise CatalogInvokeError(f"catalog function error: {function_error}")

    raw_payload = response.get("Payload")
    if raw_payload is None:
        raise CatalogInvokeError("catalog invoke returned no payload")

    body = raw_payload.read()
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CatalogInvokeError("catalog invoke returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise CatalogInvokeError("catalog invoke returned non-object payload")

    if parsed.get("ok") is False:
        status_raw = parsed.get("statusCode")
        try:
            status_code = int(status_raw)
        except (TypeError, ValueError) as exc:
            raise CatalogInvokeError("catalog invoke returned invalid statusCode") from exc
        raise CatalogInvokeHttpError(
            status_code=status_code,
            code=str(parsed.get("code") or "error"),
            message=str(parsed.get("message") or ""),
        )

    if parsed.get("ok") is True:
        return {key: value for key, value in parsed.items() if key != "ok"}

    return parsed


def invoke_video_prepare_upload(
    *,
    user_sub: str,
    role: str,
    course_id: str,
    lesson_id: str,
    filename: str,
    content_type: str,
    filesize: int | None,
    catalog_lambda_arn: str,
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {
        "role": role,
        "courseId": course_id,
        "lessonId": lesson_id,
        "filename": filename,
        "contentType": content_type,
    }
    if filesize is not None:
        extra["filesize"] = filesize
    return _invoke_catalog_internal(
        internal=_INTERNAL_PREPARE,
        user_sub=user_sub,
        catalog_lambda_arn=catalog_lambda_arn,
        extra=extra,
    )


def invoke_video_commit_pending_upload(
    *,
    user_sub: str,
    role: str,
    course_id: str,
    lesson_id: str,
    video_key: str,
    expected_video_key: str,
    catalog_lambda_arn: str,
) -> Dict[str, Any]:
    return _invoke_catalog_internal(
        internal=_INTERNAL_COMMIT,
        user_sub=user_sub,
        catalog_lambda_arn=catalog_lambda_arn,
        extra={
            "role": role,
            "courseId": course_id,
            "lessonId": lesson_id,
            "videoKey": video_key,
            "expectedVideoKey": expected_video_key,
        },
    )


def invoke_video_prepare_mark_ready(
    *,
    user_sub: str,
    role: str,
    course_id: str,
    lesson_id: str,
    catalog_lambda_arn: str,
) -> Dict[str, Any]:
    return _invoke_catalog_internal(
        internal=_INTERNAL_PREPARE_MARK_READY,
        user_sub=user_sub,
        catalog_lambda_arn=catalog_lambda_arn,
        extra={
            "role": role,
            "courseId": course_id,
            "lessonId": lesson_id,
        },
    )


def invoke_video_apply_mark_ready(
    *,
    user_sub: str,
    role: str,
    course_id: str,
    lesson_id: str,
    video_key: str,
    catalog_lambda_arn: str,
    thumbnail_key: str | None = None,
    provider_metadata: Dict[str, Any] | None = None,
    provider_metadata_supplied: bool = False,
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {
        "role": role,
        "courseId": course_id,
        "lessonId": lesson_id,
        "videoKey": video_key,
        "providerMetadataSupplied": provider_metadata_supplied,
    }
    if thumbnail_key:
        extra["thumbnailKey"] = thumbnail_key
    if provider_metadata_supplied and provider_metadata is not None:
        extra["providerMetadata"] = provider_metadata
    return _invoke_catalog_internal(
        internal=_INTERNAL_APPLY_MARK_READY,
        user_sub=user_sub,
        catalog_lambda_arn=catalog_lambda_arn,
        extra=extra,
    )


def invoke_catalog_apigw(
    *,
    event: Dict[str, Any],
    catalog_lambda_arn: str,
) -> Dict[str, Any]:
    """Forward an API Gateway proxy event to catalog (e.g. S3 thumbnail upload-url)."""
    client = boto3.client("lambda")
    try:
        response = client.invoke(
            FunctionName=catalog_lambda_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(event).encode("utf-8"),
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("catalog_apigw_invoke_failed")
        raise CatalogInvokeError("catalog invoke failed") from exc

    status = response.get("StatusCode")
    if status != 200:
        raise CatalogInvokeError(f"catalog invoke status {status!r}")

    function_error = response.get("FunctionError")
    if function_error:
        logger.error("catalog_apigw_function_error error=%s", function_error)
        raise CatalogInvokeError(f"catalog function error: {function_error}")

    raw_payload = response.get("Payload")
    if raw_payload is None:
        raise CatalogInvokeError("catalog invoke returned no payload")

    body = raw_payload.read()
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CatalogInvokeError("catalog invoke returned invalid JSON") from exc

    if not isinstance(parsed, dict) or "statusCode" not in parsed:
        raise CatalogInvokeError("catalog invoke returned non-API-Gateway payload")

    return parsed


def invoke_video_webhook_status(
    *,
    webhook_payload: Dict[str, Any],
    catalog_lambda_arn: str,
    provider_metadata: Dict[str, Any] | None = None,
    provider_metadata_supplied: bool = False,
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {
        "webhookPayload": webhook_payload,
        "providerMetadataSupplied": provider_metadata_supplied,
    }
    if provider_metadata_supplied and provider_metadata is not None:
        extra["providerMetadata"] = provider_metadata
    return _invoke_catalog_internal(
        internal=_INTERNAL_WEBHOOK_STATUS,
        user_sub=_EDGE_SYSTEM_USER_SUB,
        catalog_lambda_arn=catalog_lambda_arn,
        extra=extra,
    )
