"""Thin httpx wrappers for the catalog API. Tests should prefer these over raw httpx
to keep request shapes consistent and to surface API responses in a typed way."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class ApiClient:
    """Wraps an httpx.Client with one method per catalog endpoint.

    All methods return the parsed httpx.Response so tests can assert on status
    code, headers, and body. Use response.json() inside tests."""

    def __init__(self, client: httpx.Client):
        self._client = client

    @property
    def raw(self) -> httpx.Client:
        return self._client

    def list_courses(self, *, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        return self._client.get("/courses", headers=headers or {})

    def list_my_courses(self, *, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Instructor dashboard list (draft + published), scoped to the authenticated user."""
        return self._client.get("/courses/mine", headers=headers or {})

    def create_course(self, *, title: str, description: str = "") -> httpx.Response:
        return self._client.post("/courses", json={"title": title, "description": description})

    def get_course(self, course_id: str) -> httpx.Response:
        return self._client.get(f"/courses/{course_id}")

    def enroll_course(self, course_id: str) -> httpx.Response:
        return self._client.post(f"/courses/{course_id}/enroll", json={})

    def update_course(self, course_id: str, *, title: str, description: str) -> httpx.Response:
        return self._client.put(
            f"/courses/{course_id}",
            json={"title": title, "description": description},
        )

    def delete_course(self, course_id: str) -> httpx.Response:
        return self._client.delete(f"/courses/{course_id}")

    def publish_course(self, course_id: str) -> httpx.Response:
        return self._client.put(f"/courses/{course_id}/publish")

    def list_lessons(self, course_id: str) -> httpx.Response:
        return self._client.get(f"/courses/{course_id}/lessons")

    def list_course_modules(self, course_id: str) -> httpx.Response:
        return self._client.get(f"/courses/{course_id}/modules")

    def list_module_quizzes(self, course_id: str) -> httpx.Response:
        """GET /courses/{courseId}/module-quizzes — publisher list (QB-L Plan 2)."""
        return self._client.get(f"/courses/{course_id}/module-quizzes")

    def create_course_module(
        self, course_id: str, *, title: str, description: str = ""
    ) -> httpx.Response:
        return self._client.post(
            f"/courses/{course_id}/modules",
            json={"title": title, "description": description},
        )

    def delete_course_module(self, course_id: str, module_id: str) -> httpx.Response:
        return self._client.delete(f"/courses/{course_id}/modules/{module_id}")

    def create_question_bank(self, course_id: str) -> httpx.Response:
        """POST /courses/{courseId}/question-banks — body optional (empty object)."""
        return self._client.post(f"/courses/{course_id}/question-banks", json={})

    def list_question_banks(self, course_id: str) -> httpx.Response:
        """GET /courses/{courseId}/question-banks — publisher list (QB-L)."""
        return self._client.get(f"/courses/{course_id}/question-banks")

    def list_question_bank_questions(self, course_id: str, bank_id: str) -> httpx.Response:
        """GET /courses/{courseId}/question-banks/{questionBankId}/questions."""
        return self._client.get(f"/courses/{course_id}/question-banks/{bank_id}/questions")

    def create_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        question_bank_id: str | None = None,
    ) -> httpx.Response:
        """POST /courses/{courseId}/modules/{moduleId}/quiz — body must include ``questionBankId``.

        Pass ``question_bank_id=...`` from ``POST .../question-banks``. Omitting it yields **400**
        with ``code: bad_request``.
        """
        body: Dict[str, Any] = {}
        if question_bank_id:
            body["questionBankId"] = question_bank_id
        return self._client.post(
            f"/courses/{course_id}/modules/{module_id}/quiz",
            json=body,
        )

    def start_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """POST /courses/{courseId}/modules/{moduleId}/quiz/start — student binding draw or reload.

        Pass ``body`` for optional flags such as ``{"retake": true}``. Defaults to ``{}``.
        """
        return self._client.post(
            f"/courses/{course_id}/modules/{module_id}/quiz/start",
            json=body if body is not None else {},
        )

    def submit_module_quiz(self, course_id: str, module_id: str, body: dict) -> httpx.Response:
        """POST /courses/{courseId}/modules/{moduleId}/quiz/submit — graded submission (QB-H)."""
        return self._client.post(
            f"/courses/{course_id}/modules/{module_id}/quiz/submit",
            json=body,
        )

    def create_draft_question(
        self,
        course_id: str,
        bank_id: str,
        *,
        prompt_text: str,
        options_json: Any,
        correct_option_key: str | None = None,
    ) -> httpx.Response:
        """POST /courses/{courseId}/question-banks/{questionBankId}/questions."""
        payload: Dict[str, Any] = {
            "promptText": prompt_text,
            "optionsJson": options_json,
        }
        if correct_option_key is not None:
            payload["correctOptionKey"] = correct_option_key
        return self._client.post(
            f"/courses/{course_id}/question-banks/{bank_id}/questions",
            json=payload,
        )

    def publish_question_bank(
        self,
        course_id: str,
        bank_id: str,
        *,
        n: int,
        module_id: str,
    ) -> httpx.Response:
        """POST /courses/{courseId}/question-banks/{questionBankId}/publish."""
        return self._client.post(
            f"/courses/{course_id}/question-banks/{bank_id}/publish",
            json={"n": n, "moduleId": module_id},
        )

    def patch_question(
        self,
        course_id: str,
        bank_id: str,
        question_id: str,
        *,
        body: Dict[str, Any],
    ) -> httpx.Response:
        """PATCH /courses/{courseId}/question-banks/{questionBankId}/questions/{questionId}."""
        return self._client.patch(
            f"/courses/{course_id}/question-banks/{bank_id}/questions/{question_id}",
            json=body,
        )

    def delete_question_bank_question(
        self,
        course_id: str,
        bank_id: str,
        question_id: str,
    ) -> httpx.Response:
        """DELETE /courses/{courseId}/question-banks/{questionBankId}/questions/{questionId}."""
        return self._client.delete(
            f"/courses/{course_id}/question-banks/{bank_id}/questions/{question_id}",
        )

    def create_lesson(self, course_id: str, *, title: str, module_id: str | None = None) -> httpx.Response:
        body: Dict[str, Any] = {"title": title}
        if module_id:
            body["moduleId"] = module_id
        return self._client.post(f"/courses/{course_id}/lessons", json=body)

    def update_lesson(self, course_id: str, lesson_id: str, *, title: str) -> httpx.Response:
        return self._client.put(
            f"/courses/{course_id}/lessons/{lesson_id}",
            json={"title": title},
        )

    def delete_lesson(self, course_id: str, lesson_id: str) -> httpx.Response:
        return self._client.delete(f"/courses/{course_id}/lessons/{lesson_id}")

    def mark_video_ready(
        self,
        course_id: str,
        lesson_id: str,
        *,
        thumbnail_key: Optional[str] = None,
    ) -> httpx.Response:
        path = f"/courses/{course_id}/lessons/{lesson_id}/video-ready"
        if thumbnail_key:
            return self._client.put(path, json={"thumbnailKey": thumbnail_key})
        return self._client.put(path)

    def get_playback(self, course_id: str, lesson_id: str) -> httpx.Response:
        return self._client.get(f"/playback/{course_id}/{lesson_id}")

    def get_upload_url(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str = "video.mp4",
        content_type: str = "video/mp4",
    ) -> httpx.Response:
        return self._client.post(
            "/upload-url",
            json={
                "courseId": course_id,
                "lessonId": lesson_id,
                "filename": filename,
                "contentType": content_type,
            },
        )

    def get_lesson_thumbnail_upload_url(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str = "thumb.jpg",
        content_type: str = "image/jpeg",
    ) -> httpx.Response:
        return self._client.post(
            "/upload-url",
            json={
                "courseId": course_id,
                "lessonId": lesson_id,
                "uploadKind": "lessonThumbnail",
                "filename": filename,
                "contentType": content_type,
            },
        )

    def get_users_me(self, *, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        return self._client.get("/users/me", headers=headers or {})

    def thumbnail_ready(self, course_id: str, thumbnail_key: str) -> httpx.Response:
        """Mark a course thumbnail as ready after upload.

        Args:
            course_id: The course ID
            thumbnail_key: The S3 key for the thumbnail (must start with {courseId}/thumbnail/)
        """
        return self._client.put(
            f"/courses/{course_id}/thumbnail-ready",
            json={"thumbnailKey": thumbnail_key},
        )

    def get_course_progress(self, course_id: str) -> httpx.Response:
        """Get aggregated progress for a course.

        Args:
            course_id: The course ID
        """
        return self._client.get(f"/courses/{course_id}/progress")

    def update_lesson_progress(
        self,
        course_id: str,
        lesson_id: str,
        *,
        position: int,
        duration: int,
        mark_complete: bool = False,
        mark_incomplete: bool = False,
    ) -> httpx.Response:
        """Update lesson progress (watch position and completion state).

        Args:
            course_id: The course ID
            lesson_id: The lesson ID
            position: Current watch position in seconds (>= 0)
            duration: Total lesson duration in seconds (>= 0)
            mark_complete: Set to True to explicitly mark lesson complete
            mark_incomplete: Set to True to explicitly mark lesson incomplete
        """
        return self._client.put(
            f"/courses/{course_id}/lessons/{lesson_id}/progress",
            json={
                "position": position,
                "duration": duration,
                "markComplete": mark_complete,
                "markIncomplete": mark_incomplete,
            },
        )

    def get_course_thumbnail_upload_url(
        self,
        *,
        course_id: str,
        filename: str = "cover.jpg",
        content_type: str = "image/jpeg",
    ) -> httpx.Response:
        """Request a presigned upload URL for a course thumbnail.

        Args:
            course_id: The course ID
            filename: Name of the thumbnail file (default: cover.jpg)
            content_type: MIME type of the image (default: image/jpeg)
        """
        return self._client.post(
            "/upload-url",
            json={
                "courseId": course_id,
                "filename": filename,
                "contentType": content_type,
                "uploadKind": "thumbnail",
            },
        )

    def options(self, path: str, *, origin: Optional[str] = None) -> httpx.Response:
        headers: Dict[str, str] = {}
        if origin is not None:
            headers["Origin"] = origin
        return self._client.options(path, headers=headers)


def list_lesson_ids_by_title_prefix(
    api: ApiClient, course_id: str, title_prefix: str
) -> List[str]:
    """Return lesson ids whose title starts with the given prefix; useful for
    cleanup paths that need to remove only test-created lessons."""
    resp = api.list_lessons(course_id)
    if resp.status_code != 200:
        return []
    items: List[Dict[str, Any]] = resp.json()
    return [str(item["id"]) for item in items if str(item.get("title", "")).startswith(title_prefix)]
