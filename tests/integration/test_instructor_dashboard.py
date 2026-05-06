"""Instructor dashboard tests for GET /courses/mine.

Tests the instructor's "My Courses" endpoint which returns all courses
(both DRAFT and PUBLISHED) belonging to the authenticated teacher.
"""

from __future__ import annotations

from helpers.api import ApiClient
from helpers.factories import make_test_title


def test_mine_lists_only_own_courses(api: ApiClient, alt_api: ApiClient, course_factory) -> None:
    """Teacher A only sees their courses via /courses/mine, not Teacher B's courses."""
    # Teacher A creates courses via the factory
    course_a1 = course_factory(label="teacher-a-course-1")
    course_a2 = course_factory(label="teacher-a-course-2")

    # Teacher B creates courses directly
    resp_b1 = alt_api.create_course(title=make_test_title("teacher-b-course-1"))
    assert resp_b1.status_code == 201, f"Failed to create Teacher B course 1: {resp_b1.text}"
    course_b1_id = resp_b1.json()["id"]

    resp_b2 = alt_api.create_course(title=make_test_title("teacher-b-course-2"))
    assert resp_b2.status_code == 201, f"Failed to create Teacher B course 2: {resp_b2.text}"
    course_b2_id = resp_b2.json()["id"]

    # Teacher A fetches /courses/mine
    resp = api.list_my_courses()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    courses = resp.json()

    # Teacher A should only see their own courses
    course_ids = {str(c["id"]) for c in courses}
    assert str(course_a1.course_id) in course_ids, "Teacher A should see course_a1"
    assert str(course_a2.course_id) in course_ids, "Teacher A should see course_a2"
    assert course_b1_id not in course_ids, "Teacher A should NOT see Teacher B's course 1"
    assert course_b2_id not in course_ids, "Teacher A should NOT see Teacher B's course 2"

    # Cleanup: Teacher B deletes their courses
    alt_api.delete_course(course_b1_id)
    alt_api.delete_course(course_b2_id)


def test_mine_includes_draft_and_published(api: ApiClient, lesson_factory) -> None:
    """GET /courses/mine returns both DRAFT and PUBLISHED courses."""
    # Create a draft course
    draft_resp = api.create_course(title=make_test_title("draft-course"))
    assert draft_resp.status_code == 201, f"Failed to create draft course: {draft_resp.text}"
    draft_id = draft_resp.json()["id"]

    # Create a course that will be published
    published_resp = api.create_course(title=make_test_title("published-course"))
    assert published_resp.status_code == 201, f"Failed to create published course: {published_resp.text}"
    published_id = published_resp.json()["id"]

    # Add a lesson and mark video ready for the course to be publishable
    lesson = lesson_factory(published_id, label="publishable-lesson")

    # Get upload URL to set videoKey (required before marking video ready)
    upload_resp = api.get_upload_url(course_id=published_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"Failed to get upload URL: {upload_resp.text}"

    ready_resp = api.mark_video_ready(published_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"Failed to mark video ready: {ready_resp.text}"

    # Publish the course
    publish_resp = api.publish_course(published_id)
    assert publish_resp.status_code == 200, f"Failed to publish course: {publish_resp.text}"

    # Fetch /courses/mine
    resp = api.list_my_courses()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    courses = resp.json()

    # Find both courses in the response
    courses_by_id = {str(c["id"]): c for c in courses}

    assert str(draft_id) in courses_by_id, "Draft course should appear in /courses/mine"
    assert str(published_id) in courses_by_id, "Published course should appear in /courses/mine"

    # Verify statuses
    assert courses_by_id[str(draft_id)]["status"] == "DRAFT", "Draft course should have status DRAFT"
    assert courses_by_id[str(published_id)]["status"] == "PUBLISHED", "Published course should have status PUBLISHED"


def test_mine_returns_empty_for_new_teacher(alt_api: ApiClient) -> None:
    """New teacher with no courses gets an empty list from /courses/mine."""
    # Teacher B (new teacher) fetches /courses/mine
    resp = alt_api.list_my_courses()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    courses = resp.json()

    # Should be an empty list (or at least no test-prefixed courses)
    assert isinstance(courses, list), "Response should be a list"
    # Filter out any non-test courses that might exist from other sources
    test_courses = [c for c in courses if str(c.get("title", "")).startswith("integration-test-")]
    assert len(test_courses) == 0, "New teacher should have no test courses"


def test_mine_sorted_by_created_at(api: ApiClient, course_factory) -> None:
    """Courses in /courses/mine are ordered oldest-first (by createdAt ascending)."""
    # Create multiple courses in sequence (should have different timestamps)
    course1 = course_factory(label="sorted-course-1")
    course2 = course_factory(label="sorted-course-2")
    course3 = course_factory(label="sorted-course-3")

    # Fetch /courses/mine
    resp = api.list_my_courses()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    courses = resp.json()

    # Filter to only our test courses
    test_course_ids = {str(c.course_id) for c in [course1, course2, course3]}
    test_courses = [c for c in courses if str(c["id"]) in test_course_ids]

    # Verify all three courses are present
    assert len(test_courses) >= 3, f"Expected at least 3 test courses, got {len(test_courses)}"

    # Extract the ones we just created in the order they appear
    found_course_ids = [str(c["id"]) for c in test_courses if str(c["id"]) in test_course_ids]

    # Verify the order: course1 (oldest), course2, course3 (newest)
    expected_order = [str(course1.course_id), str(course2.course_id), str(course3.course_id)]

    # Check that courses appear in ascending createdAt order (oldest first)
    # Note: We verify by checking the relative positions in the list
    positions = {cid: found_course_ids.index(cid) for cid in expected_order}
    assert positions[str(course1.course_id)] < positions[str(course2.course_id)], \
        "course1 should appear before course2 (oldest-first ordering)"
    assert positions[str(course2.course_id)] < positions[str(course3.course_id)], \
        "course2 should appear before course3 (oldest-first ordering)"
