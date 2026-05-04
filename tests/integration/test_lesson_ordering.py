"""S5 regression coverage for the lesson SK / order refactor in repo.py.

History: previously, the DynamoDB sort key was LESSON#{order:03d} and
`create_lesson` computed `next_order = len(existing) + 1`. Deleting a middle
lesson and creating a new one would silently overwrite an existing lesson
because the SK collided. The fix: SK is now LESSON#{lesson_id} (UUID-based),
`order` is a stored attribute, `next_order = max(existing.order, default=0) + 1`,
and `service.delete_lesson` compacts remaining lesson orders to `1..N` so the
display has no gaps. These tests are the positive regression check that the
collision can no longer happen and that compaction works."""

from __future__ import annotations

from helpers.api import ApiClient


def test_delete_middle_lesson_then_create_does_not_overwrite(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    a = lesson_factory(course.course_id, label="A")
    b = lesson_factory(course.course_id, label="B")
    c = lesson_factory(course.course_id, label="C")

    # Pre-condition: orders are 1, 2, 3 in creation order.
    assert (a.order, b.order, c.order) == (1, 2, 3)

    # Remove the middle lesson; the service compacts remaining orders to 1..N.
    del_resp = api.delete_lesson(course.course_id, b.lesson_id)
    assert del_resp.status_code == 200

    after_delete = api.list_lessons(course.course_id)
    assert after_delete.status_code == 200
    items_by_id = {item["id"]: item for item in after_delete.json()}

    # A and C must still be present and unchanged in title (not overwritten).
    assert a.lesson_id in items_by_id
    assert c.lesson_id in items_by_id
    assert items_by_id[a.lesson_id]["title"] == a.title
    assert items_by_id[c.lesson_id]["title"] == c.title

    # Compaction: A keeps order 1; C's order shifts down from 3 to 2.
    assert items_by_id[a.lesson_id]["order"] == 1
    assert items_by_id[c.lesson_id]["order"] == 2

    # Create a new lesson. It must be a brand-new row, not an overwrite.
    d = lesson_factory(course.course_id, label="D")

    final = api.list_lessons(course.course_id)
    assert final.status_code == 200
    items = final.json()
    assert len(items) == 3, "expected exactly 3 lessons after delete + create"

    items_by_id = {item["id"]: item for item in items}
    assert items_by_id[a.lesson_id]["title"] == a.title
    assert items_by_id[c.lesson_id]["title"] == c.title
    assert items_by_id[d.lesson_id]["title"] == d.title

    # Final orders are 1..N consecutive with no gaps and no duplicates.
    orders = sorted(item["order"] for item in items)
    assert orders == [1, 2, 3], f"expected compact 1..N orders, got {orders}"


def test_lessons_are_returned_sorted_by_order(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    created = [lesson_factory(course.course_id, label=f"slot{i}") for i in range(4)]

    listing = api.list_lessons(course.course_id)
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == len(created)

    # Returned items are sorted ascending by order.
    orders = [item["order"] for item in items]
    assert orders == sorted(orders)
    # And each created lesson is present.
    listed_ids = {item["id"] for item in items}
    for lh in created:
        assert lh.lesson_id in listed_ids
