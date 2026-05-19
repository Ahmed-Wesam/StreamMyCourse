"""HTTPS integration coverage for course modules (RDS catalog).

Exercises GET/POST/DELETE under /courses/{id}/modules, lesson placement via moduleId,
draft visibility parity with GET /lessons, and student read on published courses.

See tests/integration/README.md for required env (JWTs, API base URL).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import (
    require_course_modules_list,
    require_lessons_include_module_fields,
    response_json_dict,
)


def _load_course_module_rows(api: ApiClient, course_id: str) -> List[Dict[str, Any]]:
    return require_course_modules_list(api.list_course_modules(course_id))


def _load_lessons_with_module_fields(api: ApiClient, course_id: str) -> List[Dict[str, Any]]:
    return require_lessons_include_module_fields(api.list_lessons(course_id))


def _assert_module_shape(mod: Dict[str, Any]) -> None:
    for key in ("id", "title", "description", "order"):
        assert key in mod, f"missing key {key} in module: {mod!r}"


def _module_payloads_ordered(modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(modules, key=lambda m: int(m["order"]))


def test_owner_lists_default_module(api: ApiClient, course_factory) -> None:
    course = course_factory(label="mods-list-default")
    mods = _load_course_module_rows(api, course.course_id)
    assert len(mods) >= 1
    ordered = _module_payloads_ordered(mods)
    assert ordered[0]["order"] == 0
    for m in mods:
        _assert_module_shape(m)


def test_owner_creates_second_module_and_lists_sorted(api: ApiClient, course_factory) -> None:
    course = course_factory(label="mods-create-second")
    title2 = make_test_title("extra-module")
    cr = api.create_course_module(course.course_id, title=title2, description="second")
    assert cr.status_code == 201, cr.text
    body = cr.json()
    assert "moduleId" in body and body["moduleId"]
    assert "order" in body

    mods = _module_payloads_ordered(_load_course_module_rows(api, course.course_id))
    assert len(mods) == 2
    assert {m["order"] for m in mods} == {0, 1}


def test_lessons_ordered_by_module_then_lesson_order(api: ApiClient, course_factory) -> None:
    course = course_factory(label="mods-lesson-order")
    mod_list = _load_course_module_rows(api, course.course_id)
    default_id = min(mod_list, key=lambda m: m["order"])["id"]

    r_mod2 = api.create_course_module(course.course_id, title=make_test_title("mod-b"), description="")
    assert r_mod2.status_code == 201, r_mod2.text
    mod2_id = r_mod2.json()["moduleId"]

    # Lesson in higher-order module first (chronologically), then default module.
    r1 = api.create_lesson(course.course_id, title=make_test_title("in-mod2"), module_id=mod2_id)
    assert r1.status_code == 201, r1.text
    r2 = api.create_lesson(course.course_id, title=make_test_title("in-default"), module_id=default_id)
    assert r2.status_code == 201, r2.text

    rows = _load_lessons_with_module_fields(api, course.course_id)
    assert len(rows) == 2
    keys = [(int(r["moduleOrder"]), int(r["order"])) for r in rows]
    assert keys == sorted(keys)
    assert rows[0]["moduleId"] == default_id
    assert rows[1]["moduleId"] == mod2_id


def test_create_lesson_with_explicit_module_id(api: ApiClient, course_factory) -> None:
    course = course_factory(label="mods-explicit-mid")
    r_mod2 = api.create_course_module(course.course_id, title=make_test_title("target-mod"), description="")
    assert r_mod2.status_code == 201, r_mod2.text
    target = r_mod2.json()["moduleId"]

    lesson_title = make_test_title("placed")
    lr = api.create_lesson(course.course_id, title=lesson_title, module_id=target)
    assert lr.status_code == 201, lr.text
    body = lr.json()
    placed_id = body["moduleId"]
    assert placed_id == target
    lesson_id = body["lessonId"]

    listed = _load_lessons_with_module_fields(api, course.course_id)
    row = next(x for x in listed if x["id"] == lesson_id)
    assert row["moduleId"] == target


def test_create_lesson_without_module_id_targets_default_module(api: ApiClient, course_factory) -> None:
    course = course_factory(label="mods-default-mid")
    mods = _module_payloads_ordered(_load_course_module_rows(api, course.course_id))
    default_id = mods[0]["id"]

    lr = api.create_lesson(course.course_id, title=make_test_title("implicit-mod"))
    assert lr.status_code == 201, lr.text
    assert lr.json()["moduleId"] == default_id


def test_delete_non_last_module_removes_only_that_module(
    api: ApiClient, course_factory
) -> None:
    course = course_factory(label="mods-delete-nonlast")
    r2 = api.create_course_module(course.course_id, title=make_test_title("to-delete"), description="")
    assert r2.status_code == 201, r2.text
    victim_id = r2.json()["moduleId"]

    # Video-free lesson under the module we will delete (avoids MEDIA_CLEANUP_QUEUE 503).
    lr = api.create_lesson(course.course_id, title=make_test_title("only-in-victim"), module_id=victim_id)
    assert lr.status_code == 201, lr.text
    lesson_id = lr.json()["lessonId"]

    before = _module_payloads_ordered(_load_course_module_rows(api, course.course_id))
    assert len(before) == 2

    dr = api.delete_course_module(course.course_id, victim_id)
    assert dr.status_code == 200, dr.text
    del_body = response_json_dict(dr)
    assert del_body.get("moduleId") == victim_id
    assert del_body.get("deleted") is True

    after = _module_payloads_ordered(_load_course_module_rows(api, course.course_id))
    assert len(after) == 1
    assert victim_id not in {m["id"] for m in after}

    lessons = _load_lessons_with_module_fields(api, course.course_id)
    assert lesson_id not in {x["id"] for x in lessons}


def test_delete_last_module_rejected(api: ApiClient, course_factory) -> None:
    course = course_factory(label="mods-delete-last")
    mods = _load_course_module_rows(api, course.course_id)
    assert len(mods) == 1
    only_id = mods[0]["id"]

    dr = api.delete_course_module(course.course_id, only_id)
    assert dr.status_code == 400, dr.text
    body = response_json_dict(dr)
    assert body.get("code") == "bad_request"
    assert "last module" in body.get("message", "").lower()


def test_draft_modules_parity_with_lessons_for_alt_teacher(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    course = course_factory(label="draft-mod-parity-alt")
    lessons_r = alt_api.list_lessons(course.course_id)
    modules_r = alt_api.list_course_modules(course.course_id)
    assert lessons_r.status_code == modules_r.status_code == 404
    lb = response_json_dict(lessons_r)
    mb = response_json_dict(modules_r)
    assert lb.get("code") == mb.get("code"), f"lesson body {lb!r} vs modules body {mb!r}"


def test_draft_modules_parity_with_lessons_for_student(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    course = course_factory(label="draft-mod-parity-student")
    lessons_r = student_api.list_lessons(course.course_id)
    modules_r = student_api.list_course_modules(course.course_id)
    assert lessons_r.status_code == modules_r.status_code == 404
    lb = response_json_dict(lessons_r)
    mb = response_json_dict(modules_r)
    assert lb.get("code") == mb.get("code"), f"lesson body {lb!r} vs modules body {mb!r}"


def test_student_can_list_modules_on_published_course(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    course = course_factory(label="published-mods-student")
    assert api.create_course_module(course.course_id, title=make_test_title("extra-mod"), description="").status_code == 201

    lesson = lesson_factory(course.course_id, label="pub-mod-lesson")
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200

    from helpers.billing_access import ensure_student_subscription

    ensure_student_subscription(
        api_base_url, student_api, course.course_id, lesson.lesson_id
    )

    owner_mods_list = require_course_modules_list(api.list_course_modules(course.course_id))
    assert len(owner_mods_list) >= 2

    student_mods = require_course_modules_list(student_api.list_course_modules(course.course_id))
    assert len(student_mods) >= 2
    for m in student_mods:
        _assert_module_shape(m)


def test_post_lesson_with_foreign_module_id_returns_404(api: ApiClient, course_factory) -> None:
    course = course_factory(label="bad-mid-lesson")
    bogus = str(uuid.uuid4())
    lr = api.create_lesson(course.course_id, title=make_test_title("orphan"), module_id=bogus)
    assert lr.status_code == 404, lr.text
    assert response_json_dict(lr).get("code") == "not_found"


def test_delete_unknown_module_is_200_noop(api: ApiClient, course_factory) -> None:
    """DELETE is idempotent for unknown ids: 200 no-op, modules unchanged."""
    course = course_factory(label="delete-unknown-mod")
    before = _load_course_module_rows(api, course.course_id)
    before_ids = {m["id"] for m in before}

    dr = api.delete_course_module(course.course_id, str(uuid.uuid4()))
    assert dr.status_code == 200, dr.text
    body = response_json_dict(dr)
    assert body.get("deleted") is False

    after = _load_course_module_rows(api, course.course_id)
    after_ids = {m["id"] for m in after}
    assert after_ids == before_ids

    after = _load_course_module_rows(api, course.course_id)
    assert {m["id"] for m in after} == before_ids


def test_post_lesson_with_module_from_another_course_returns_404(api: ApiClient, course_factory) -> None:
    """moduleId must belong to the target course (_resolve_module_for_new_lesson + get_course_module)."""
    course_a = course_factory(label="mods-cross-a")
    course_b = course_factory(label="mods-cross-b")
    other_module_id = _load_course_module_rows(api, course_b.course_id)[0]["id"]

    lr = api.create_lesson(course_a.course_id, title=make_test_title("wrong-course-mod"), module_id=other_module_id)
    assert lr.status_code == 404, lr.text
    assert response_json_dict(lr).get("code") == "not_found"


def test_delete_course_module_non_uuid_returns_404(api: ApiClient, course_factory) -> None:
    """Service rejects invalid module_id UUID before touching the repository."""
    course = course_factory(label="mods-delete-bad-uuid")
    dr = api.delete_course_module(course.course_id, "not-a-uuid")
    assert dr.status_code == 404, dr.text
    assert response_json_dict(dr).get("code") == "not_found"
