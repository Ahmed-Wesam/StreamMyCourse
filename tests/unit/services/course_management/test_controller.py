"""Unit tests for `services.course_management.controller`.

Two slices:
1. `_route` — the router table; we drive it directly because (a) the live
   API Gateway routing is reproduced here and (b) malformed paths can only
   reach this layer in tests.
2. `handle()` — the dispatcher; we inject a `MagicMock` service to verify
   error mapping and CORS behavior end-to-end without spinning up the
   full bootstrap.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Conflict, HttpError, NotFound
from services.course_management.controller import (
    _api_error_response,
    _route,
    handle,
)


# --- _route table ------------------------------------------------------------


class TestRouteTable:
    @pytest.mark.parametrize(
        "method,path,expected_action,expected_params",
        [
            ("GET", "/courses", "list_courses", {}),
            ("GET", "/courses/mine", "list_instructor_courses", {}),
            ("POST", "/courses", "create_course", {}),
            ("GET", "/courses/abc-123/preview", "get_course_preview", {"courseId": "abc-123"}),
            ("POST", "/courses/abc-123/enroll", "enroll_course", {"courseId": "abc-123"}),
            ("GET", "/courses/abc-123", "get_course", {"courseId": "abc-123"}),
            ("PUT", "/courses/abc-123", "update_course", {"courseId": "abc-123"}),
            ("DELETE", "/courses/abc-123", "delete_course", {"courseId": "abc-123"}),
            (
                "PUT",
                "/courses/abc-123/publish",
                "publish_course",
                {"courseId": "abc-123"},
            ),
            (
                "PUT",
                "/courses/abc-123/thumbnail-ready",
                "mark_thumbnail_ready",
                {"courseId": "abc-123"},
            ),
            (
                "GET",
                "/courses/abc-123/lessons",
                "list_lessons",
                {"courseId": "abc-123"},
            ),
            (
                "POST",
                "/courses/abc-123/lessons",
                "create_lesson",
                {"courseId": "abc-123"},
            ),
            (
                "PUT",
                "/courses/abc-123/lessons/lid-9",
                "update_lesson",
                {"courseId": "abc-123", "lessonId": "lid-9"},
            ),
            (
                "DELETE",
                "/courses/abc-123/lessons/lid-9",
                "delete_lesson",
                {"courseId": "abc-123", "lessonId": "lid-9"},
            ),
            (
                "PUT",
                "/courses/abc-123/lessons/lid-9/video-ready",
                "mark_video_ready",
                {"courseId": "abc-123", "lessonId": "lid-9"},
            ),
            (
                "GET",
                "/playback/abc-123/lid-9",
                "get_playback",
                {"courseId": "abc-123", "lessonId": "lid-9"},
            ),
            ("POST", "/upload-url", "get_upload_url", {}),
        ],
    )
    def test_each_supported_route_maps_correctly(
        self,
        method: str,
        path: str,
        expected_action: str,
        expected_params: Dict[str, str],
    ) -> None:
        action, params = _route(method, path)
        assert action == expected_action
        assert params == expected_params

    @pytest.mark.parametrize(
        "method,path",
        [
            # Wrong verb on a known path.
            ("DELETE", "/courses"),
            ("PATCH", "/courses/abc"),
            # API Gateway would normally pre-filter these, but the unit layer
            # is the only place we can pin them.
            ("GET", "/unknown"),
            ("GET", "/courses/abc/extra/parts/here"),
            ("PUT", "/courses/abc/lessons/lid/typo"),
            ("GET", "/playback"),
            ("GET", "/playback/onlycourse"),
            ("POST", "/upload-url/extra"),
            ("GET", ""),  # empty path
            ("", "/courses"),  # empty method
        ],
    )
    def test_unknown_routes_yield_not_found(self, method: str, path: str) -> None:
        action, params = _route(method, path)
        assert action == "not_found"
        assert params == {}

    def test_root_path_is_not_found(self) -> None:
        action, params = _route("GET", "/")
        assert action == "not_found"
        assert params == {}


# --- _api_error_response error mapping --------------------------------------


class TestApiErrorResponse:
    def test_bad_request_maps_to_400_with_code_and_cors(self) -> None:
        resp = _api_error_response(BadRequest("missing field", code="X"), "https://app")
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body == {"message": "missing field", "code": "X"}
        # CORS headers come along for the ride.
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://app"

    def test_not_found_maps_to_404(self) -> None:
        resp = _api_error_response(NotFound("Lesson not found"), "*")
        assert resp["statusCode"] == 404
        body = json.loads(resp["body"])
        assert body["message"] == "Lesson not found"
        assert body["code"] == "not_found"

    def test_conflict_maps_to_409(self) -> None:
        resp = _api_error_response(Conflict("dup"), "*")
        assert resp["statusCode"] == 409
        body = json.loads(resp["body"])
        assert body == {"message": "dup", "code": "conflict"}

    def test_http_error_with_no_code_omits_code(self) -> None:
        resp = _api_error_response(HttpError(418, "teapot"), "*")
        body = json.loads(resp["body"])
        assert body == {"message": "teapot"}
        assert resp["statusCode"] == 418


# --- handle() end-to-end with mock service ----------------------------------


@pytest.fixture
def svc() -> MagicMock:
    return MagicMock()


class TestHandleDispatch:
    def test_options_short_circuits_to_204(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        evt = make_lambda_event(method="OPTIONS", path="/courses")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 204
        # No service interaction on preflight.
        svc.assert_not_called()

    def test_unknown_route_returns_404_via_not_found(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        evt = make_lambda_event(method="GET", path="/totally-unknown")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 404
        body = json.loads(resp["body"])
        assert body["code"] == "not_found"

    def test_bad_request_from_service_maps_to_400(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.list_published_courses.side_effect = BadRequest("bad", code="X")
        evt = make_lambda_event(method="GET", path="/courses")
        resp = handle(evt, origin="https://app", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body == {"message": "bad", "code": "X"}
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://app"

    def test_not_found_from_service_maps_to_404(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.get_course_detail_with_enrollment.side_effect = NotFound("Course not found")
        evt = make_lambda_event(method="GET", path="/courses/missing")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 404
        body = json.loads(resp["body"])
        assert body["code"] == "not_found"

    def test_conflict_from_service_maps_to_409(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.delete_course.side_effect = Conflict("clash")
        evt = make_lambda_event(method="DELETE", path="/courses/c1")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 409
        body = json.loads(resp["body"])
        assert body == {"message": "clash", "code": "conflict"}

    def test_unhandled_exception_returns_500_internal_error(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.list_published_courses.side_effect = RuntimeError("kaboom")
        evt = make_lambda_event(method="GET", path="/courses")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert body == {"message": "Internal error", "code": "internal_error"}

    def test_list_courses_passes_through_dto_envelope(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.list_published_courses.return_value = [
            {"id": "c1", "title": "T", "description": "D", "status": "PUBLISHED"}
        ]
        evt = make_lambda_event(method="GET", path="/courses")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert isinstance(body, list)
        assert body[0]["id"] == "c1"
        assert body[0]["status"] == "PUBLISHED"

    def test_list_instructor_courses_200(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.list_instructor_courses.return_value = [
            {"id": "d1", "title": "Draft", "description": "", "status": "DRAFT"}
        ]
        evt = make_lambda_event(method="GET", path="/courses/mine")
        evt["requestContext"]["authorizer"] = {
            "claims": {"sub": "t1", "custom:role": "teacher"}
        }
        resp = handle(
            evt,
            origin="*",
            svc=svc,
            video_bucket="b",
            auth_svc=MagicMock(),
            auth_enforced=True,
        )
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body[0]["id"] == "d1"
        svc.list_instructor_courses.assert_called_once_with(
            cognito_sub="t1", role="teacher", auth_enforced=True
        )

    def test_list_instructor_courses_forbidden_for_student(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        evt = make_lambda_event(method="GET", path="/courses/mine")
        evt["requestContext"]["authorizer"] = {
            "claims": {"sub": "s1", "custom:role": "student"}
        }
        resp = handle(
            evt,
            origin="*",
            svc=svc,
            video_bucket="b",
            auth_svc=MagicMock(),
            auth_enforced=True,
        )
        assert resp["statusCode"] == 403
        svc.list_instructor_courses.assert_not_called()

    def test_create_lesson_201_status(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.create_lesson.return_value = {"lessonId": "lid", "order": 1}
        evt = make_lambda_event(
            method="POST",
            path="/courses/c1/lessons",
            body={"title": "Intro"},
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body == {"lessonId": "lid", "order": 1}

    def test_upload_url_requires_course_and_lesson_ids(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        # Missing courseId/lessonId → 400 before svc is ever called.
        evt = make_lambda_event(method="POST", path="/upload-url", body={})
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "required" in body["message"].lower()
        svc.get_upload_url.assert_not_called()
        svc.get_thumbnail_upload_url.assert_not_called()
        svc.get_lesson_thumbnail_upload_url.assert_not_called()

    def test_upload_url_lesson_thumbnail_kind(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.get_lesson_thumbnail_upload_url.return_value = {
            "uploadUrl": "https://signed.example/lthumb",
            "thumbnailKey": (
                "c1/lessons/lid/thumbnail/"
                "22222222-2222-4222-8222-222222222222.jpg"
            ),
        }
        evt = make_lambda_event(
            method="POST",
            path="/upload-url",
            body={
                "courseId": "c1",
                "lessonId": "lid",
                "uploadKind": "lessonThumbnail",
                "filename": "thumb.jpg",
                "contentType": "image/jpeg",
            },
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["thumbnailKey"].startswith("c1/lessons/lid/thumbnail/")
        svc.get_lesson_thumbnail_upload_url.assert_called_once_with(
            course_id="c1",
            lesson_id="lid",
            filename="thumb.jpg",
            content_type="image/jpeg",
        )
        svc.get_upload_url.assert_not_called()

    def test_upload_url_thumbnail_kind_skips_lesson_id(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.get_thumbnail_upload_url.return_value = {
            "uploadUrl": "https://signed.example/thumb",
            "thumbnailKey": "c1/thumbnail/33333333-3333-4333-8333-333333333333.jpg",
        }
        evt = make_lambda_event(
            method="POST",
            path="/upload-url",
            body={
                "courseId": "c1",
                "uploadKind": "thumbnail",
                "filename": "pic.jpg",
                "contentType": "image/jpeg",
            },
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["thumbnailKey"].startswith("c1/thumbnail/")
        svc.get_thumbnail_upload_url.assert_called_once_with(
            course_id="c1", filename="pic.jpg", content_type="image/jpeg"
        )
        svc.get_upload_url.assert_not_called()

    def test_upload_url_supplies_filename_default_when_blank(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.get_upload_url.return_value = {
            "uploadUrl": "https://signed.example/put",
            "videoKey": "c1/lessons/lid/video/11111111-1111-4111-8111-111111111111.mp4",
        }
        evt = make_lambda_event(
            method="POST",
            path="/upload-url",
            body={"courseId": "c1", "lessonId": "lid", "contentType": ""},
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        # Empty contentType must be coerced to a sensible default by the controller.
        kwargs = svc.get_upload_url.call_args.kwargs
        assert kwargs["content_type"] == "video/mp4"
        assert kwargs["filename"] == "video.mp4"

    def test_method_falls_back_to_legacy_http_method_field(
        self, svc: MagicMock
    ) -> None:
        svc.list_published_courses.return_value = []
        # API Gateway v1-style event: `httpMethod` + `path` instead of v2's
        # `requestContext.http.method` + `rawPath`.
        evt: Dict[str, Any] = {
            "httpMethod": "GET",
            "path": "/courses",
            "headers": {},
        }
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200


class TestHandleDispatchPerAction:
    """One quick test per remaining action arm to pin the mapping (status,
    method delegation, and DTO envelope) without re-asserting CORS."""

    def test_create_course_201(self, svc: MagicMock, make_lambda_event) -> None:
        svc.create_course.return_value = {"id": "c1", "status": "DRAFT"}
        evt = make_lambda_event(
            method="POST",
            path="/courses",
            body={"title": "T", "description": "D"},
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 201
        svc.create_course.assert_called_once_with("T", "D", created_by="")

    def test_get_course_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.get_course_detail_with_enrollment.return_value = {
            "id": "c1",
            "title": "T",
            "description": "D",
            "status": "PUBLISHED",
            "enrolled": False,
        }
        evt = make_lambda_event(method="GET", path="/courses/c1")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.get_course_detail_with_enrollment.assert_called_once_with(
            "c1",
            cognito_sub="",
            role="student",
            auth_enforced=False,
        )

    def test_update_course_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.update_course.return_value = {"id": "c1", "updated": True}
        evt = make_lambda_event(
            method="PUT",
            path="/courses/c1",
            body={"title": "T2", "description": "D2"},
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.update_course.assert_called_once_with("c1", "T2", "D2")

    def test_publish_course_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.publish_course.return_value = {"id": "c1", "status": "PUBLISHED"}
        evt = make_lambda_event(method="PUT", path="/courses/c1/publish")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.publish_course.assert_called_once_with("c1")

    def test_delete_course_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.delete_course.return_value = {"id": "c1", "deleted": True}
        evt = make_lambda_event(method="DELETE", path="/courses/c1")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.delete_course.assert_called_once_with("c1")

    def test_delete_course_404_not_found(self, svc: MagicMock, make_lambda_event) -> None:
        svc.delete_course.side_effect = NotFound("Course not found")
        evt = make_lambda_event(method="DELETE", path="/courses/missing")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 404

    def test_list_lessons_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.list_lessons.return_value = [
            {"id": "lid", "title": "T", "order": 1, "videoStatus": "pending"}
        ]
        evt = make_lambda_event(method="GET", path="/courses/c1/lessons")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body[0]["id"] == "lid"
        svc.ensure_can_view_lessons_and_playback.assert_called_once_with(
            "c1",
            cognito_sub="",
            role="student",
            auth_enforced=False,
        )

    def test_update_lesson_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.update_lesson.return_value = {"lessonId": "lid", "updated": True}
        evt = make_lambda_event(
            method="PUT",
            path="/courses/c1/lessons/lid",
            body={"title": "T"},
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.update_lesson.assert_called_once_with("c1", "lid", "T")

    def test_delete_lesson_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.delete_lesson.return_value = {"lessonId": "lid", "deleted": True}
        evt = make_lambda_event(method="DELETE", path="/courses/c1/lessons/lid")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.delete_lesson.assert_called_once_with("c1", "lid")

    def test_mark_video_ready_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.mark_lesson_video_ready.return_value = {
            "lessonId": "lid",
            "videoStatus": "ready",
        }
        evt = make_lambda_event(
            method="PUT", path="/courses/c1/lessons/lid/video-ready"
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.mark_lesson_video_ready.assert_called_once_with(
            "c1", "lid", thumbnail_key=None
        )

    def test_mark_video_ready_passes_thumbnail_key(self, svc: MagicMock, make_lambda_event) -> None:
        svc.mark_lesson_video_ready.return_value = {
            "lessonId": "lid",
            "videoStatus": "ready",
        }
        tk = "c1/lessons/lid/thumbnail/44444444-4444-4444-8444-444444444444.jpg"
        evt = make_lambda_event(
            method="PUT",
            path="/courses/c1/lessons/lid/video-ready",
            body={"thumbnailKey": tk},
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.mark_lesson_video_ready.assert_called_once_with("c1", "lid", thumbnail_key=tk)

    def test_get_playback_passes_video_bucket(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.get_playback_url.return_value = {"url": "https://signed/x"}
        evt = make_lambda_event(method="GET", path="/playback/c1/lid")
        resp = handle(evt, origin="*", svc=svc, video_bucket="my-bucket", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.ensure_can_view_lessons_and_playback.assert_called_once_with(
            "c1",
            cognito_sub="",
            role="student",
            auth_enforced=False,
        )
        svc.get_playback_url.assert_called_once_with(
            "c1", "lid", video_bucket="my-bucket"
        )

    def test_get_course_preview_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.get_course_preview.return_value = {
            "id": "c1",
            "title": "T",
            "description": "D",
            "status": "PUBLISHED",
            "lessonsPreview": [{"id": "l1", "title": "L", "order": 1}],
        }
        evt = make_lambda_event(method="GET", path="/courses/c1/preview")
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.get_course_preview.assert_called_once_with("c1")

    def test_enroll_course_200(self, svc: MagicMock, make_lambda_event) -> None:
        auth = MagicMock()
        auth.get_or_create_profile.return_value = {"userId": "user-1"}
        svc.enroll_in_published_course.return_value = {"courseId": "c1", "enrolled": True}
        evt = make_lambda_event(method="POST", path="/courses/c1/enroll")
        evt["requestContext"]["authorizer"] = {
            "claims": {"sub": "user-1", "email": "a@b.com", "custom:role": "student"}
        }
        resp = handle(
            evt,
            origin="*",
            svc=svc,
            video_bucket="b",
            auth_svc=auth,
            auth_enforced=True,
        )
        assert resp["statusCode"] == 200
        auth.get_or_create_profile.assert_called_once_with(
            user_sub="user-1", email="a@b.com", role="student"
        )
        svc.enroll_in_published_course.assert_called_once_with("c1", cognito_sub="user-1")

    def test_enroll_calls_get_or_create_profile_before_enroll_in_published_course(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        """Defense-in-depth: ensure users row exists before enroll FK insert."""
        auth = MagicMock()
        order: list[str] = []

        def _prof(**kwargs):
            order.append("profile")
            return {}

        def _enroll(*a, **k):
            order.append("enroll")
            return {"courseId": "c1", "enrolled": True}

        auth.get_or_create_profile.side_effect = _prof
        svc.enroll_in_published_course.side_effect = _enroll
        evt = make_lambda_event(method="POST", path="/courses/c1/enroll")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "u1"}}
        handle(
            evt,
            origin="*",
            svc=svc,
            video_bucket="b",
            auth_svc=auth,
            auth_enforced=True,
        )
        assert order == ["profile", "enroll"]

    def test_upload_url_happy_path_passes_kwargs(
        self, svc: MagicMock, make_lambda_event
    ) -> None:
        svc.get_upload_url.return_value = {
            "uploadUrl": "https://signed/put",
            "videoKey": "c1/lessons/lid/video/11111111-1111-4111-8111-111111111111.mp4",
        }
        evt = make_lambda_event(
            method="POST",
            path="/upload-url",
            body={
                "courseId": "c1",
                "lessonId": "lid",
                "filename": "intro.mp4",
                "contentType": "video/mp4",
            },
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        svc.get_upload_url.assert_called_once_with(
            course_id="c1",
            lesson_id="lid",
            filename="intro.mp4",
            content_type="video/mp4",
        )

    def test_mark_thumbnail_ready_200(self, svc: MagicMock, make_lambda_event) -> None:
        svc.mark_course_thumbnail_ready.return_value = {
            "id": "c1",
            "thumbnailReady": True,
        }
        evt = make_lambda_event(
            method="PUT",
            path="/courses/c1/thumbnail-ready",
            body={
                "thumbnailKey": "c1/thumbnail/55555555-5555-4555-8555-555555555555.jpg"
            },
        )
        resp = handle(evt, origin="*", svc=svc, video_bucket="b", auth_svc=MagicMock())
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body == {"id": "c1", "thumbnailReady": True}
        svc.mark_course_thumbnail_ready.assert_called_once_with(
            "c1", "c1/thumbnail/55555555-5555-4555-8555-555555555555.jpg"
        )
