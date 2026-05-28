"""API Gateway path resolution for video provider edge."""

from __future__ import annotations

from apigw_path import apigw_routing_path

_COURSE_ID = "11111111-1111-4111-8111-111111111111"
_LESSON_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def test_apigw_routing_path_prefers_literal_path_over_template_resource_path() -> None:
    path = apigw_routing_path(
        {
            "path": f"/courses/{_COURSE_ID}/lessons/{_LESSON_ID}/video-ready",
            "requestContext": {
                "resourcePath": "/courses/{courseId}/lessons/{lessonId}/video-ready",
                "stage": "dev",
            },
        }
    )
    assert path == f"/courses/{_COURSE_ID}/lessons/{_LESSON_ID}/video-ready"
