"""Unit tests for ApiClient integration helper.

These tests verify URL path construction, JSON body shapes, and header passing
using mocked httpx.Client (no real AWS calls).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call

from tests.integration.helpers.api import ApiClient


class TestApiClient(unittest.TestCase):
    """Test suite for ApiClient methods."""

    def setUp(self) -> None:
        """Set up mock httpx client for each test."""
        self.mock_client = MagicMock()
        self.api = ApiClient(self.mock_client)

    def test_thumbnail_ready_sends_put(self) -> None:
        """Verify thumbnail_ready sends PUT to /courses/{id}/thumbnail-ready with correct body."""
        course_id = "course-123"
        thumbnail_key = "course-123/thumbnail/cover.jpg"

        self.api.thumbnail_ready(course_id, thumbnail_key)

        expected_call = call.put(
            f"/courses/{course_id}/thumbnail-ready",
            json={"thumbnailKey": thumbnail_key},
        )
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_get_course_progress_sends_get(self) -> None:
        """Verify get_course_progress sends GET to /courses/{id}/progress."""
        course_id = "course-456"

        self.api.get_course_progress(course_id)

        expected_call = call.get(f"/courses/{course_id}/progress")
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_update_lesson_progress_sends_put_with_body(self) -> None:
        """Verify update_lesson_progress sends PUT with correct JSON body."""
        course_id = "course-789"
        lesson_id = "lesson-abc"
        position = 120
        duration = 300

        self.api.update_lesson_progress(
            course_id, lesson_id, position=position, duration=duration
        )

        expected_call = call.put(
            f"/courses/{course_id}/lessons/{lesson_id}/progress",
            json={
                "position": position,
                "duration": duration,
                "markComplete": False,
                "markIncomplete": False,
            },
        )
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_update_lesson_progress_with_mark_complete(self) -> None:
        """Verify update_lesson_progress handles mark_complete=True."""
        course_id = "course-789"
        lesson_id = "lesson-abc"
        position = 280
        duration = 300

        self.api.update_lesson_progress(
            course_id, lesson_id, position=position, duration=duration, mark_complete=True
        )

        expected_call = call.put(
            f"/courses/{course_id}/lessons/{lesson_id}/progress",
            json={
                "position": position,
                "duration": duration,
                "markComplete": True,
                "markIncomplete": False,
            },
        )
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_update_lesson_progress_with_mark_incomplete(self) -> None:
        """Verify update_lesson_progress handles mark_incomplete=True."""
        course_id = "course-789"
        lesson_id = "lesson-abc"
        position = 0
        duration = 300

        self.api.update_lesson_progress(
            course_id, lesson_id, position=position, duration=duration, mark_incomplete=True
        )

        expected_call = call.put(
            f"/courses/{course_id}/lessons/{lesson_id}/progress",
            json={
                "position": position,
                "duration": duration,
                "markComplete": False,
                "markIncomplete": True,
            },
        )
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_get_course_thumbnail_upload_url_sends_post(self) -> None:
        """Verify get_course_thumbnail_upload_url sends POST with uploadKind: thumbnail."""
        course_id = "course-xyz"
        filename = "cover.jpg"
        content_type = "image/jpeg"

        self.api.get_course_thumbnail_upload_url(
            course_id=course_id, filename=filename, content_type=content_type
        )

        expected_call = call.post(
            "/upload-url",
            json={
                "courseId": course_id,
                "filename": filename,
                "contentType": content_type,
                "uploadKind": "thumbnail",
            },
        )
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_get_course_thumbnail_upload_url_uses_defaults(self) -> None:
        """Verify get_course_thumbnail_upload_url uses default filename and content_type."""
        course_id = "course-xyz"

        self.api.get_course_thumbnail_upload_url(course_id=course_id)

        expected_call = call.post(
            "/upload-url",
            json={
                "courseId": course_id,
                "filename": "cover.jpg",
                "contentType": "image/jpeg",
                "uploadKind": "thumbnail",
            },
        )
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_update_lesson_progress_with_zero_position(self) -> None:
        """Verify update_lesson_progress handles position=0 correctly."""
        course_id = "course-789"
        lesson_id = "lesson-abc"

        self.api.update_lesson_progress(
            course_id, lesson_id, position=0, duration=300
        )

        expected_call = call.put(
            f"/courses/{course_id}/lessons/{lesson_id}/progress",
            json={
                "position": 0,
                "duration": 300,
                "markComplete": False,
                "markIncomplete": False,
            },
        )
        self.assertEqual(self.mock_client.method_calls, [expected_call])

    def test_update_lesson_progress_passes_response_through(self) -> None:
        """Verify update_lesson_progress returns the httpx.Response from the client."""
        mock_response = MagicMock()
        self.mock_client.put.return_value = mock_response

        result = self.api.update_lesson_progress(
            "course-1", "lesson-1", position=10, duration=100
        )

        self.assertEqual(result, mock_response)

    def test_thumbnail_ready_passes_response_through(self) -> None:
        """Verify thumbnail_ready returns the httpx.Response from the client."""
        mock_response = MagicMock()
        self.mock_client.put.return_value = mock_response

        result = self.api.thumbnail_ready("course-1", "key/path.jpg")

        self.assertEqual(result, mock_response)

    def test_get_course_progress_passes_response_through(self) -> None:
        """Verify get_course_progress returns the httpx.Response from the client."""
        mock_response = MagicMock()
        self.mock_client.get.return_value = mock_response

        result = self.api.get_course_progress("course-1")

        self.assertEqual(result, mock_response)

    def test_get_course_thumbnail_upload_url_passes_response_through(self) -> None:
        """Verify get_course_thumbnail_upload_url returns the httpx.Response from the client."""
        mock_response = MagicMock()
        self.mock_client.post.return_value = mock_response

        result = self.api.get_course_thumbnail_upload_url(course_id="course-1")

        self.assertEqual(result, mock_response)


if __name__ == "__main__":
    unittest.main()
