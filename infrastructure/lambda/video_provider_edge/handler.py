"""Video provider edge Lambda — upload-url (slice 1) and video-ready (slice 2)."""



from __future__ import annotations



import json

import hmac

import logging

from typing import Any, Dict, Tuple



from video_catalog_invoke import (

    CatalogInvokeError,

    CatalogInvokeHttpError,

    invoke_video_apply_mark_ready,

    invoke_video_commit_pending_upload,

    invoke_video_prepare_mark_ready,

    invoke_video_webhook_status,

    invoke_video_prepare_upload,

)

from video_edge_config import VideoProviderEdgeConfig, load_video_provider_edge_config

from kinescope_http import (

    KinescopeUploadError,

    KinescopeUploadInit,

    KinescopeVideoMetadata,

    delete_kinescope_video,

    fetch_video_metadata,

    init_kinescope_lesson_upload,

    video_status_confirms_done,

    webhook_status_confirmed_by_api,

)



logger = logging.getLogger(__name__)



_load_config = load_video_provider_edge_config

_invoke_video_prepare_upload = invoke_video_prepare_upload

_invoke_video_commit_pending_upload = invoke_video_commit_pending_upload

_invoke_video_prepare_mark_ready = invoke_video_prepare_mark_ready

_invoke_video_apply_mark_ready = invoke_video_apply_mark_ready

_invoke_video_webhook_status = invoke_video_webhook_status

_init_kinescope_upload = init_kinescope_lesson_upload

_fetch_kinescope_metadata = fetch_video_metadata

_delete_kinescope_video = delete_kinescope_video



_UPLOAD_POST_PATH = "/upload-url"

_WEBHOOK_POST_PATH = "/webhooks/kinescope"

_CSP_API = "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"





def _json_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:

    return {

        "statusCode": status_code,

        "headers": {

            "content-type": "application/json",

            "X-Content-Type-Options": "nosniff",

            "X-Frame-Options": "DENY",

            "Content-Security-Policy": _CSP_API,

            "Cache-Control": "no-store",

        },

        "body": json.dumps(body),

    }





def _error_response(status_code: int, code: str, message: str) -> Dict[str, Any]:

    return _json_response(status_code, {"code": code, "message": message})





def _options_response(

    event: Dict[str, Any],

    cfg: VideoProviderEdgeConfig,

    *,

    allow_methods: str,

) -> Dict[str, Any]:

    headers = event.get("headers") or {}

    origin = _header_lookup(headers, "Origin") if isinstance(headers, dict) else ""

    if not origin and cfg.cors_allow_origin:

        origin = cfg.cors_allow_origin

    response_headers: Dict[str, str] = {

        "X-Content-Type-Options": "nosniff",

        "X-Frame-Options": "DENY",

        "Content-Security-Policy": _CSP_API,

    }

    if origin:

        response_headers["Access-Control-Allow-Origin"] = origin

        response_headers["Access-Control-Allow-Methods"] = allow_methods

        response_headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"

        if origin.startswith("https://"):

            response_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return {

        "statusCode": 204,

        "headers": response_headers,

        "body": "",

    }





def _apigw_routing_path(event: Dict[str, Any]) -> str:

    rc = event.get("requestContext") or {}

    resource_path = rc.get("resourcePath")

    if isinstance(resource_path, str) and resource_path.startswith("/"):

        return resource_path

    path = event.get("path")

    if isinstance(path, str) and path.startswith("/"):

        return path

    raw = event.get("rawPath")

    if isinstance(raw, str) and raw.startswith("/"):

        return raw

    return "/"





def _normalize_headers(event: Dict[str, Any]) -> Dict[str, str]:

    raw = event.get("headers") or {}

    if not isinstance(raw, dict):

        return {}

    return {str(k).lower(): str(v) for k, v in raw.items() if v is not None}





def _extract_webhook_secret(event: Dict[str, Any]) -> str:

    headers = _normalize_headers(event)

    header_val = headers.get("x-kinescope-webhook-secret", "").strip()

    qs = event.get("queryStringParameters") or {}

    query_val = ""

    if isinstance(qs, dict):

        query_val = str(qs.get("token") or qs.get("secret") or "").strip()

    return header_val or query_val





def _verify_webhook_secret(event: Dict[str, Any], configured_secret: str) -> bool:

    secret = (configured_secret or "").strip()

    if not secret:

        return True

    provided = _extract_webhook_secret(event)

    return hmac.compare_digest(provided, secret)





def _header_lookup(headers: Dict[str, Any], name: str) -> str:

    if not isinstance(headers, dict):

        return ""

    target = name.lower()

    for key, value in headers.items():

        if isinstance(key, str) and key.lower() == target and value is not None:

            return str(value).strip()

    return ""





def _claims_sub(event: Dict[str, Any]) -> str:

    rc = event.get("requestContext") or {}

    authorizer = rc.get("authorizer") if isinstance(rc, dict) else {}

    if not isinstance(authorizer, dict):

        return ""

    claims = authorizer.get("claims")

    if isinstance(claims, dict):

        return str(claims.get("sub") or "").strip()

    if isinstance(claims, str) and claims.strip():

        try:

            parsed = json.loads(claims)

            if isinstance(parsed, dict):

                return str(parsed.get("sub") or "").strip()

        except json.JSONDecodeError:

            pass

    return str(authorizer.get("sub") or "").strip()





def _claims_role(event: Dict[str, Any]) -> str:

    rc = event.get("requestContext") or {}

    authorizer = rc.get("authorizer") if isinstance(rc, dict) else {}

    if not isinstance(authorizer, dict):

        return "student"

    claims = authorizer.get("claims")

    if isinstance(claims, dict):

        return str(claims.get("custom:role") or claims.get("role") or "student").strip().lower()

    return "student"





def _parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:

    body = event.get("body")

    if body is None or body == "":

        return {}

    if not isinstance(body, str):

        raise ValueError("invalid body")

    try:

        parsed = json.loads(body)

    except json.JSONDecodeError as exc:

        raise ValueError("invalid json") from exc

    if not isinstance(parsed, dict):

        raise ValueError("invalid body")

    return parsed





def _parse_video_ready_path(path: str) -> Tuple[str, str] | None:

    parts = path.strip("/").split("/")

    if (

        len(parts) == 5

        and parts[0] == "courses"

        and parts[2] == "lessons"

        and parts[4] == "video-ready"

    ):

        course_id = parts[1].strip()

        lesson_id = parts[3].strip()

        if course_id and lesson_id:

            return course_id, lesson_id

    return None





def _metadata_to_invoke_payload(metadata: KinescopeVideoMetadata) -> Dict[str, Any]:

    payload: Dict[str, Any] = {"status": metadata.status}

    if metadata.duration_seconds is not None:

        payload["durationSeconds"] = metadata.duration_seconds

    return payload





def _handle_upload_url(event: Dict[str, Any], cfg: VideoProviderEdgeConfig) -> Dict[str, Any]:

    user_sub = _claims_sub(event)

    if not user_sub:

        return _error_response(401, "unauthorized", "Missing authenticated user")



    catalog_arn = str(cfg.catalog_lambda_arn or "").strip()

    if not cfg.is_configured():

        return _error_response(503, "video_unconfigured", "Video uploads are not configured")



    try:

        payload = _parse_json_body(event)

    except ValueError:

        return _error_response(400, "invalid_request", "Invalid JSON body")



    course_id = str(payload.get("courseId") or "").strip()

    lesson_id = str(payload.get("lessonId") or "").strip()

    if not course_id or not lesson_id:

        return _error_response(400, "invalid_request", "courseId and lessonId are required")



    filename = str(payload.get("filename") or "video.mp4").strip() or "video.mp4"

    content_type = str(payload.get("contentType") or "video/mp4").strip() or "video/mp4"

    filesize: int | None = None

    if "filesize" in payload and payload.get("filesize") is not None:

        try:

            filesize = int(payload.get("filesize"))

        except (TypeError, ValueError):

            return _error_response(400, "invalid_request", "filesize must be a positive integer")

        if filesize <= 0:

            return _error_response(400, "invalid_request", "filesize must be a positive integer")



    role = _claims_role(event)



    try:

        prepared = _invoke_video_prepare_upload(

            user_sub=user_sub,

            role=role,

            course_id=course_id,

            lesson_id=lesson_id,

            filename=filename,

            content_type=content_type,

            filesize=filesize,

            catalog_lambda_arn=catalog_arn,

        )

    except CatalogInvokeHttpError as exc:

        return _error_response(exc.status_code, exc.code, exc.message)

    except CatalogInvokeError:

        return _error_response(503, "video_unconfigured", "Video uploads are not configured")



    expected_video_key = str(prepared.get("expectedVideoKey") or "").strip()



    try:

        init: KinescopeUploadInit = _init_kinescope_upload(

            api_token=str(cfg.kinescope_api_token or ""),

            parent_id=str(cfg.kinescope_parent_id or ""),

            filename=filename,

            filesize=filesize,

        )

    except KinescopeUploadError:

        return _error_response(503, "video_unconfigured", "Video uploads are not configured")



    try:

        _invoke_video_commit_pending_upload(

            user_sub=user_sub,

            role=role,

            course_id=course_id,

            lesson_id=lesson_id,

            video_key=init.video_key,

            expected_video_key=expected_video_key,

            catalog_lambda_arn=catalog_arn,

        )

    except CatalogInvokeHttpError as exc:

        if exc.status_code == 409 and exc.code in ("upload_conflict", "conflict"):

            _delete_kinescope_video(

                api_token=str(cfg.kinescope_api_token or ""),

                video_id=init.video_key,

            )

            return _error_response(409, "upload_conflict", exc.message)

        return _error_response(exc.status_code, exc.code, exc.message)

    except CatalogInvokeError:

        return _error_response(503, "video_unconfigured", "Video uploads are not configured")



    return _json_response(

        200,

        {

            "uploadUrl": init.upload_url,

            "videoKey": init.video_key,

            "uploadMethod": init.upload_method,

            "provider": "kinescope",

        },

    )





def _handle_mark_ready(event: Dict[str, Any], cfg: VideoProviderEdgeConfig) -> Dict[str, Any]:

    user_sub = _claims_sub(event)

    if not user_sub:

        return _error_response(401, "unauthorized", "Missing authenticated user")



    catalog_arn = str(cfg.catalog_lambda_arn or "").strip()

    if not cfg.is_configured():

        return _error_response(503, "video_unconfigured", "Video mark-ready is not configured")



    path = _apigw_routing_path(event)

    parsed_path = _parse_video_ready_path(path)

    if parsed_path is None:

        return _error_response(404, "not_found", "Not found")

    course_id, lesson_id = parsed_path



    try:

        body = _parse_json_body(event)

    except ValueError:

        return _error_response(400, "invalid_request", "Invalid JSON body")



    thumbnail_key = str(body.get("thumbnailKey") or "").strip() or None

    role = _claims_role(event)



    try:

        prepared = _invoke_video_prepare_mark_ready(

            user_sub=user_sub,

            role=role,

            course_id=course_id,

            lesson_id=lesson_id,

            catalog_lambda_arn=catalog_arn,

        )

    except CatalogInvokeHttpError as exc:

        return _error_response(exc.status_code, exc.code, exc.message)

    except CatalogInvokeError:

        return _error_response(503, "video_unconfigured", "Video mark-ready is not configured")



    video_key = str(prepared.get("videoKey") or "").strip()

    if not video_key:

        return _error_response(400, "invalid_request", "No video uploaded for lesson")



    metadata = _fetch_kinescope_metadata(

        api_token=str(cfg.kinescope_api_token or ""),

        video_id=video_key,

    )



    provider_metadata_supplied = False

    provider_metadata_payload: Dict[str, Any] | None = None



    if cfg.deployment_environment == "prod":

        if metadata is None or not video_status_confirms_done(metadata.status):

            return _error_response(400, "video_not_ready", "Video is still processing")

        provider_metadata_supplied = True

        provider_metadata_payload = _metadata_to_invoke_payload(metadata)

    elif metadata is not None and video_status_confirms_done(metadata.status):

        provider_metadata_supplied = True

        provider_metadata_payload = _metadata_to_invoke_payload(metadata)



    try:

        result = _invoke_video_apply_mark_ready(

            user_sub=user_sub,

            role=role,

            course_id=course_id,

            lesson_id=lesson_id,

            video_key=video_key,

            catalog_lambda_arn=catalog_arn,

            thumbnail_key=thumbnail_key,

            provider_metadata=provider_metadata_payload,

            provider_metadata_supplied=provider_metadata_supplied,

        )

    except CatalogInvokeHttpError as exc:

        return _error_response(exc.status_code, exc.code, exc.message)

    except CatalogInvokeError:

        return _error_response(503, "video_unconfigured", "Video mark-ready is not configured")



    return _json_response(200, result)





def _is_video_ready_path(path: str) -> bool:

    return _parse_video_ready_path(path) is not None





def _handle_kinescope_webhook(event: Dict[str, Any], cfg: VideoProviderEdgeConfig) -> Dict[str, Any]:

    if not _verify_webhook_secret(event, str(cfg.kinescope_webhook_secret or "")):

        return _error_response(401, "unauthorized", "Invalid webhook secret")



    catalog_arn = str(cfg.catalog_lambda_arn or "").strip()

    if not cfg.is_webhook_configured():

        return _error_response(503, "video_unconfigured", "Video webhooks are not configured")



    try:

        body = _parse_json_body(event)

    except ValueError:

        return _error_response(400, "invalid_request", "Invalid JSON body")



    data = body.get("data")

    if not isinstance(data, dict):

        return _error_response(400, "invalid_request", "Invalid webhook payload")



    status = str(data.get("status") or "").strip().lower()

    provider_metadata_supplied = False

    provider_metadata_payload: Dict[str, Any] | None = None



    if status in ("done", "error", "aborted"):

        video_id = str(data.get("id") or "").strip()

        if not video_id:

            return _error_response(400, "invalid_request", "Missing Kinescope video id")



        metadata = _fetch_kinescope_metadata(

            api_token=str(cfg.kinescope_api_token or ""),

            video_id=video_id,

        )

        if metadata is None:

            return _json_response(200, {"ignored": True, "reason": "verification_failed"})

        if not webhook_status_confirmed_by_api(status, metadata.status):

            return _json_response(200, {"ignored": True, "reason": "status_mismatch"})

        provider_metadata_supplied = True

        provider_metadata_payload = _metadata_to_invoke_payload(metadata)



    try:

        result = _invoke_video_webhook_status(

            webhook_payload=body,

            catalog_lambda_arn=catalog_arn,

            provider_metadata=provider_metadata_payload,

            provider_metadata_supplied=provider_metadata_supplied,

        )

    except CatalogInvokeHttpError as exc:

        return _error_response(exc.status_code, exc.code, exc.message)

    except CatalogInvokeError:

        logger.exception("kinescope webhook catalog invoke failed")

        return _error_response(500, "internal_error", "Webhook processing failed")



    return _json_response(200, result)





def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:

    """API Gateway proxy entry point."""

    logging.getLogger().setLevel(logging.INFO)

    _ = context



    cfg = _load_config()

    method = (event.get("httpMethod") or "").upper()

    path = _apigw_routing_path(event)

    video_ready = _is_video_ready_path(path)



    if not cfg.is_configured() and method in ("POST", "PUT", "OPTIONS"):

        if path == _UPLOAD_POST_PATH or video_ready:

            return _error_response(503, "video_unconfigured", "Video provider edge is not configured")



    if method == "OPTIONS" and path == _WEBHOOK_POST_PATH:

        return _options_response(event, cfg, allow_methods="POST,OPTIONS")

    if method == "POST" and path == _WEBHOOK_POST_PATH:

        return _handle_kinescope_webhook(event, cfg)



    if method == "OPTIONS" and path == _UPLOAD_POST_PATH:

        return _options_response(event, cfg, allow_methods="POST,OPTIONS")

    if method == "POST" and path == _UPLOAD_POST_PATH:

        return _handle_upload_url(event, cfg)

    if method == "OPTIONS" and video_ready:

        return _options_response(event, cfg, allow_methods="PUT,OPTIONS")

    if method == "PUT" and video_ready:

        return _handle_mark_ready(event, cfg)



    return _error_response(404, "not_found", "Not found")

