"""Certificate entitlement is a purchase, not course ownership or playback access."""

from __future__ import annotations

from services.certificates.entitlement import is_certificate_entitled
from services.course_management.models import Course


def test_paid_course_purchase_entitles_an_unpublished_course() -> None:
    assert (
        is_certificate_entitled(
            has_paid_course_purchase=True,
            has_paid_bundle=False,
            course_published=False,
        )
        is True
    )


def test_paid_bundle_entitles_a_published_course_only() -> None:
    assert (
        is_certificate_entitled(
            has_paid_course_purchase=False,
            has_paid_bundle=True,
            course_published=True,
        )
        is True
    )
    assert (
        is_certificate_entitled(
            has_paid_course_purchase=False,
            has_paid_bundle=True,
            course_published=False,
        )
        is False
    )


def test_bundle_keeps_an_unpublished_course_the_student_already_started() -> None:
    assert (
        is_certificate_entitled(
            has_paid_course_purchase=False,
            has_paid_bundle=True,
            course_published=False,
            has_course_activity=True,
        )
        is True
    )


def test_no_purchase_is_not_entitled_even_when_published() -> None:
    assert (
        is_certificate_entitled(
            has_paid_course_purchase=False,
            has_paid_bundle=False,
            course_published=True,
        )
        is False
    )


class _Courses:
    def __init__(self, courses: list[Course]) -> None:
        self._courses = courses

    def list_courses(self) -> list[Course]:
        return list(self._courses)

    def get_course(self, course_id: str) -> Course | None:
        for course in self._courses:
            if course.id == course_id:
                return course
        return None


class _Purchases:
    def __init__(
        self,
        course_purchases: set[tuple[str, str]],
        bundle_users: set[str],
    ) -> None:
        self._course_purchases = course_purchases
        self._bundle_users = bundle_users

    def has_paid_course_purchase(self, user_sub: str, course_id: str) -> bool:
        return (user_sub, course_id) in self._course_purchases

    def has_paid_bundle(self, user_sub: str) -> bool:
        return user_sub in self._bundle_users


def _course(course_id: str, status: str, created_by: str) -> Course:
    return Course(
        id=course_id,
        title=course_id,
        description="",
        status=status,
        createdBy=created_by,
    )


def test_owner_and_admin_without_a_purchase_are_not_entitled() -> None:
    from bootstrap import _CertificateEntitledAdapter

    teacher = "teacher-owner"
    draft = _course("draft-course", "DRAFT", teacher)
    published = _course("live-course", "PUBLISHED", teacher)
    adapter = _CertificateEntitledAdapter(
        _Courses([draft, published]),
        _Purchases(set(), set()),
    )

    assert adapter.is_entitled(teacher, draft.id) is False
    assert adapter.is_entitled(teacher, published.id) is False
    assert adapter.list_entitled_course_ids(teacher) == []
    assert adapter.list_entitled_course_ids("admin-sub") == []


def test_paid_student_of_an_unpublished_course_is_entitled() -> None:
    from bootstrap import _CertificateEntitledAdapter

    draft = _course("draft-course", "DRAFT", "teacher-owner")
    adapter = _CertificateEntitledAdapter(
        _Courses([draft]),
        _Purchases({("student-1", draft.id)}, set()),
    )

    assert adapter.is_entitled("student-1", draft.id) is True
    assert adapter.list_entitled_course_ids("student-1") == [draft.id]


def test_bundle_lists_published_courses_and_hides_drafts() -> None:
    from bootstrap import _CertificateEntitledAdapter

    draft = _course("draft-course", "DRAFT", "teacher-owner")
    published = _course("live-course", "PUBLISHED", "teacher-owner")
    adapter = _CertificateEntitledAdapter(
        _Courses([draft, published]),
        _Purchases(set(), {"student-1"}),
    )

    assert adapter.is_entitled("student-1", draft.id) is False
    assert adapter.is_entitled("student-1", published.id) is True
    assert adapter.list_entitled_course_ids("student-1") == [published.id]


def test_bundle_keeps_unpublished_course_with_existing_activity() -> None:
    from bootstrap import _CertificateEntitledAdapter

    draft = _course("draft-course", "DRAFT", "teacher-owner")
    untouched = _course("other-draft", "DRAFT", "teacher-owner")

    def activity(user_sub: str, course_id: str) -> bool:
        return user_sub == "student-1" and course_id == draft.id

    adapter = _CertificateEntitledAdapter(
        _Courses([draft, untouched]),
        _Purchases(set(), {"student-1"}),
        activity,
    )

    assert adapter.is_entitled("student-1", draft.id) is True
    assert adapter.is_entitled("student-1", untouched.id) is False
    assert adapter.list_entitled_course_ids("student-1") == [draft.id]


def test_course_activity_is_a_quiz_attempt_or_an_assignment_submission() -> None:
    from bootstrap import _certificate_has_course_activity

    class _QuizScores:
        def __init__(self) -> None:
            self.scores: dict[tuple[str, str], dict] = {}

        def list_submitted_attempt_scores_by_module(
            self, *, course_id: str, user_sub: str
        ) -> dict:
            return self.scores.get((user_sub, course_id), {})

    class _AssignmentRows:
        def __init__(self) -> None:
            self.rows: set[tuple[str, str]] = set()

        def user_has_submission_for_course(self, *, course_id: str, user_sub: str) -> bool:
            return (user_sub, course_id) in self.rows

    quizzes = _QuizScores()
    assignments = _AssignmentRows()
    has_activity = _certificate_has_course_activity(quizzes, assignments)
    assert has_activity("student-1", "draft-course") is False
    quizzes.scores[("student-1", "draft-course")] = {
        "m1": [{"correctCount": 1, "totalCount": 1}]
    }
    assert has_activity("student-1", "draft-course") is True
    quizzes.scores.clear()
    assignments.rows.add(("student-1", "draft-course"))
    assert has_activity("student-1", "draft-course") is True


def test_user_has_submission_for_course_filters_by_student_and_course() -> None:
    from services.assignments.rds_repo import AssignmentsRdsRepository

    repo = AssignmentsRdsRepository(lambda: None)
    captured: dict[str, object] = {}

    class _Cursor:
        def fetchone(self) -> tuple[int] | None:
            return captured.get("row")  # type: ignore[return-value]

    def _execute(sql: str, params: tuple = (), *, commit: bool = False) -> _Cursor:
        captured["sql"] = sql
        captured["params"] = params
        return _Cursor()

    repo._execute = _execute  # type: ignore[method-assign]
    captured["row"] = (1,)
    assert repo.user_has_submission_for_course(course_id="course-1", user_sub="student-1") is True
    sql = str(captured["sql"])
    assert "assignment_submissions" in sql
    assert "course_id" in sql
    assert "user_sub" in sql
    assert captured["params"] == ("course-1", "student-1")
    captured["row"] = None
    assert repo.user_has_submission_for_course(course_id="course-1", user_sub="student-1") is False
