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

    def create_course(self, *, title: str, description: str = "") -> httpx.Response:
        return self._client.post("/courses", json={"title": title, "description": description})

    def get_course(self, course_id: str) -> httpx.Response:
        return self._client.get(f"/courses/{course_id}")

    def get_course_preview(self, course_id: str) -> httpx.Response:
        return self._client.get(f"/courses/{course_id}/preview")

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

    def create_lesson(self, course_id: str, *, title: str) -> httpx.Response:
        return self._client.post(f"/courses/{course_id}/lessons", json={"title": title})

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
