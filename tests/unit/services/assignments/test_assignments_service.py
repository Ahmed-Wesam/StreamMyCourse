"""RS-13 assignments service behavior tests (fakes only; no AWS/Postgres)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence
from uuid import uuid4

import pytest

from services.assignments.ports import (
    AssignmentRow,
    CourseOwnerInfo,
    CriterionRow,
    GradeRow,
    GradeScoreRow,
    NotifyMailMessage,
    ObjectHead,
    SubmissionFileRow,
    SubmissionRow,
)
from services.assignments.service import AssignmentsService
from services.assignments.validation import sanitize_rich_html, score_percent_half_up
from services.common.errors import BadRequest, Conflict, Forbidden, NotFound

_COURSE = "11111111-1111-1111-1111-111111111111"
_MOD1 = "22222222-2222-2222-2222-222222222221"
_MOD2 = "22222222-2222-2222-2222-222222222222"
_TEACHER = "teacher-owner"
_STUDENT = "student-1"
_OTHER = "student-2"
_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self) -> None:
        self.objects: Dict[str, ObjectHead] = {}
        self.put_calls: list[tuple[str, str, int]] = []
        self.deleted: list[str] = []

    def presign_put(self, key: str, content_type: str, content_length: int) -> str:
        self.put_calls.append((key, content_type, content_length))
        return f"https://upload.example/{key}"

    def head(self, key: str) -> Optional[ObjectHead]:
        return self.objects.get(key)

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    def presign_get(
        self,
        key: str,
        *,
        disposition: str,
        download_filename: str,
        expires_seconds: int,
    ) -> str:
        return f"https://get.example/{key}?d={disposition}&n={download_filename}&e={expires_seconds}"


class FakeCleanup:
    def __init__(self, url: str = "https://sqs.example/cleanup") -> None:
        self._url = url
        self.enqueued: list[list[str]] = []

    def queue_url(self) -> str:
        return self._url

    def enqueue_object_keys(self, keys: Sequence[str]) -> None:
        self.enqueued.append(list(keys))


class FakeMail:
    def __init__(self) -> None:
        self.messages: list[NotifyMailMessage] = []
        self.raise_on_enqueue = False

    def enqueue_notify(self, message: NotifyMailMessage) -> None:
        if self.raise_on_enqueue:
            raise RuntimeError("sqs down")
        self.messages.append(message)


class FakeUserEmail:
    def __init__(self, emails: Dict[str, str] | None = None) -> None:
        self.emails = emails or {_STUDENT: "student@example.com"}

    def get_email_for_user_sub(self, user_sub: str) -> str:
        return self.emails.get(user_sub, "")


class FakeCourseAccess:
    def __init__(self) -> None:
        self.allowed: set[tuple[str, str]] = {(_STUDENT, _COURSE), (_OTHER, _COURSE)}

    def has_course_access(self, user_sub: str, course_id: str, role: str) -> bool:
        return (user_sub, course_id) in self.allowed


class FakeQuizLock:
    def __init__(self) -> None:
        # module_id -> locked
        self.locked: Dict[str, bool] = {_MOD1: False, _MOD2: True}

    def is_module_locked_for_student(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> bool:
        return bool(self.locked.get(module_id, False))


class FakeCourseLookup:
    def __init__(self) -> None:
        self.course = CourseOwnerInfo(
            id=_COURSE, title="Stats 101", created_by=_TEACHER
        )
        self.modules = {_MOD1, _MOD2}

    def get_course(self, course_id: str) -> Optional[CourseOwnerInfo]:
        if course_id != self.course.id:
            return None
        return self.course

    def module_belongs_to_course(self, course_id: str, module_id: str) -> bool:
        return course_id == _COURSE and module_id in self.modules


class InMemoryAssignmentsRepo:
    def __init__(self) -> None:
        self.assignments: Dict[str, AssignmentRow] = {}
        self.submissions: Dict[str, SubmissionRow] = {}
        self.files: Dict[str, SubmissionFileRow] = {}
        self.grades: Dict[str, GradeRow] = {}

    def count_assignments_for_course(self, course_id: str) -> int:
        return sum(1 for a in self.assignments.values() if a.course_id == course_id)

    def list_assignments(
        self, course_id: str, *, published_only: bool = False
    ) -> List[AssignmentRow]:
        rows = [a for a in self.assignments.values() if a.course_id == course_id]
        if published_only:
            rows = [a for a in rows if a.status == "published"]
        return sorted(rows, key=lambda a: a.created_at)

    def get_assignment(
        self, course_id: str, assignment_id: str
    ) -> Optional[AssignmentRow]:
        a = self.assignments.get(assignment_id)
        if a is None or a.course_id != course_id:
            return None
        return a

    def insert_assignment(
        self,
        *,
        course_id: str,
        module_id: str,
        title: str,
        pass_percent: int,
        counts_toward_certificate: bool,
        status: str = "draft",
    ) -> AssignmentRow:
        row = AssignmentRow(
            id=str(uuid4()),
            course_id=course_id,
            module_id=module_id,
            title=title,
            status=status,
            pass_percent=pass_percent,
            counts_toward_certificate=counts_toward_certificate,
            instructions_mode="plain",
            instructions_text="",
            instructions_html="",
            instructions_image_key="",
            instructions_image_ready=False,
            rubric_mode="plain",
            rubric_text="",
            rubric_html="",
            rubric_image_key="",
            rubric_image_ready=False,
            created_at=_NOW,
            updated_at=_NOW,
            criteria=(),
        )
        self.assignments[row.id] = row
        return row

    def update_assignment(self, row: AssignmentRow) -> AssignmentRow:
        self.assignments[row.id] = row
        return row

    def delete_assignment(self, course_id: str, assignment_id: str) -> bool:
        a = self.assignments.get(assignment_id)
        if a is None or a.course_id != course_id:
            return False
        del self.assignments[assignment_id]
        return True

    def list_object_keys_for_assignment(
        self, course_id: str, assignment_id: str
    ) -> List[str]:
        a = self.get_assignment(course_id, assignment_id)
        if a is None:
            return []
        keys = [a.instructions_image_key, a.rubric_image_key]
        for f in self.files.values():
            if f.assignment_id == assignment_id and f.object_key:
                keys.append(f.object_key)
        return [k for k in keys if k]

    def replace_criteria(
        self,
        *,
        assignment_id: str,
        criteria: Sequence[tuple[str, str, int]],
    ) -> List[CriterionRow]:
        rows = [
            CriterionRow(
                id=cid,
                assignment_id=assignment_id,
                label=label,
                max_points=pts,
                sort_order=i,
            )
            for i, (cid, label, pts) in enumerate(criteria)
        ]
        a = self.assignments[assignment_id]
        self.assignments[assignment_id] = replace(a, criteria=tuple(rows))
        return rows

    def list_criteria(self, assignment_id: str) -> List[CriterionRow]:
        a = self.assignments.get(assignment_id)
        return list(a.criteria) if a else []

    def get_latest_submission_for_user(
        self, *, assignment_id: str, user_sub: str
    ) -> Optional[SubmissionRow]:
        rows = [
            s
            for s in self.submissions.values()
            if s.assignment_id == assignment_id and s.user_sub == user_sub
        ]
        if not rows:
            return None
        rows.sort(key=lambda s: s.created_at, reverse=True)
        return self._hydrate(rows[0])

    def get_submission(
        self, *, course_id: str, assignment_id: str, submission_id: str
    ) -> Optional[SubmissionRow]:
        s = self.submissions.get(submission_id)
        if s is None or s.course_id != course_id or s.assignment_id != assignment_id:
            return None
        return self._hydrate(s)

    def list_submissions_for_assignment(
        self, *, course_id: str, assignment_id: str
    ) -> List[SubmissionRow]:
        return [
            self._hydrate(s)
            for s in self.submissions.values()
            if s.course_id == course_id and s.assignment_id == assignment_id
        ]

    def list_submissions_for_user(
        self, *, course_id: str, assignment_id: str, user_sub: str
    ) -> List[SubmissionRow]:
        return [
            self._hydrate(s)
            for s in self.submissions.values()
            if s.course_id == course_id
            and s.assignment_id == assignment_id
            and s.user_sub == user_sub
        ]

    def insert_submission(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_sub: str,
        status: str = "draft",
    ) -> SubmissionRow:
        # enforce one draft
        for s in self.submissions.values():
            if (
                s.assignment_id == assignment_id
                and s.user_sub == user_sub
                and s.status == "draft"
            ):
                raise Conflict("draft exists")
        row = SubmissionRow(
            id=str(uuid4()),
            assignment_id=assignment_id,
            course_id=course_id,
            user_sub=user_sub,
            status=status,
            note="",
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.submissions[row.id] = row
        return row

    def update_submission(self, row: SubmissionRow) -> SubmissionRow:
        self.submissions[row.id] = replace(row, files=(), grade=None)
        return self._hydrate(self.submissions[row.id])

    def count_files_for_submission(self, submission_id: str) -> int:
        return sum(1 for f in self.files.values() if f.submission_id == submission_id)

    def insert_submission_file(
        self,
        *,
        file_id: str,
        submission_id: str,
        assignment_id: str,
        course_id: str,
        title: str,
        file_type: str,
        object_key: str,
        content_type: str,
        byte_size: int,
        status: str = "pending",
    ) -> SubmissionFileRow:
        row = SubmissionFileRow(
            id=file_id,
            submission_id=submission_id,
            assignment_id=assignment_id,
            course_id=course_id,
            title=title,
            file_type=file_type,
            object_key=object_key,
            content_type=content_type,
            byte_size=byte_size,
            status=status,
            created_at=_NOW,
        )
        self.files[file_id] = row
        return row

    def get_submission_file(
        self, *, submission_id: str, file_id: str
    ) -> Optional[SubmissionFileRow]:
        f = self.files.get(file_id)
        if f is None or f.submission_id != submission_id:
            return None
        return f

    def mark_submission_file_ready(
        self, *, submission_id: str, file_id: str
    ) -> SubmissionFileRow:
        f = self.files[file_id]
        ready = replace(f, status="ready")
        self.files[file_id] = ready
        return ready

    def insert_grade(
        self,
        *,
        submission_id: str,
        assignment_id: str,
        course_id: str,
        score_percent: int,
        pass_percent: int,
        passed: bool,
        feedback: str,
        graded_by: str,
        scores: Sequence[tuple[str, int]],
    ) -> GradeRow:
        if submission_id in self.grades:
            raise Conflict("already graded")
        grade = GradeRow(
            id=str(uuid4()),
            submission_id=submission_id,
            assignment_id=assignment_id,
            course_id=course_id,
            score_percent=score_percent,
            pass_percent=pass_percent,
            passed=passed,
            feedback=feedback,
            graded_by=graded_by,
            graded_at=_NOW,
            scores=tuple(
                GradeScoreRow(criterion_id=c, points=p) for c, p in scores
            ),
        )
        self.grades[submission_id] = grade
        return grade

    def get_grade_for_submission(self, submission_id: str) -> Optional[GradeRow]:
        return self.grades.get(submission_id)

    def _hydrate(self, s: SubmissionRow) -> SubmissionRow:
        files = tuple(
            f for f in self.files.values() if f.submission_id == s.id
        )
        grade = self.grades.get(s.id)
        return replace(s, files=files, grade=grade)


@pytest.fixture
def harness() -> dict:
    repo = InMemoryAssignmentsRepo()
    storage = FakeStorage()
    cleanup = FakeCleanup()
    mail = FakeMail()
    user_email = FakeUserEmail()
    access = FakeCourseAccess()
    lock = FakeQuizLock()
    courses = FakeCourseLookup()
    svc = AssignmentsService(
        repo=repo,
        storage=storage,
        course_access=access,
        quiz_lock=lock,
        course_lookup=courses,
        cleanup=cleanup,
        mail=mail,
        user_email=user_email,
    )
    return {
        "svc": svc,
        "repo": repo,
        "storage": storage,
        "cleanup": cleanup,
        "mail": mail,
        "user_email": user_email,
        "access": access,
        "lock": lock,
        "courses": courses,
    }


def _create_publishable(h: dict, *, module_id: str = _MOD1, flag: bool = False) -> str:
    svc: AssignmentsService = h["svc"]
    created = svc.create_assignment(
        _COURSE,
        title="Lab report",
        module_id=module_id,
        counts_toward_certificate=flag,
        cognito_sub=_TEACHER,
        role="teacher",
    )
    aid = created["assignment"]["id"]
    svc.update_assignment(
        _COURSE,
        aid,
        cognito_sub=_TEACHER,
        role="teacher",
        body={
            "instructions": {"mode": "plain", "text": "Write the report."},
            "criteria": [
                {"label": "Clarity", "maxPoints": 50},
                {"label": "Method", "maxPoints": 50},
            ],
            "status": "published",
        },
    )
    return aid


class TestPublishRules:
    def test_publish_requires_instructions_and_criteria(self, harness: dict) -> None:
        svc: AssignmentsService = harness["svc"]
        created = svc.create_assignment(
            _COURSE,
            title="Draft only",
            module_id=_MOD1,
            cognito_sub=_TEACHER,
            role="teacher",
        )
        aid = created["assignment"]["id"]
        with pytest.raises(BadRequest) as exc:
            svc.publish_assignment(
                _COURSE, aid, cognito_sub=_TEACHER, role="teacher"
            )
        assert exc.value.code == "instructions_required"

        svc.update_assignment(
            _COURSE,
            aid,
            cognito_sub=_TEACHER,
            role="teacher",
            body={"instructions": {"mode": "plain", "text": "Do the work"}},
        )
        with pytest.raises(BadRequest) as exc2:
            svc.publish_assignment(
                _COURSE, aid, cognito_sub=_TEACHER, role="teacher"
            )
        assert exc2.value.code == "criteria_required"

        out = svc.update_assignment(
            _COURSE,
            aid,
            cognito_sub=_TEACHER,
            role="teacher",
            body={
                "criteria": [{"label": "Quality", "maxPoints": 10}],
                "status": "published",
            },
        )
        assert out["assignment"]["status"] == "published"


class TestCertificateFlags:
    def test_two_counts_toward_certificate_both_save(self, harness: dict) -> None:
        a1 = _create_publishable(harness, flag=True)
        a2 = _create_publishable(harness, flag=True)
        listed = harness["svc"].list_assignments(
            _COURSE, cognito_sub=_TEACHER, role="teacher"
        )
        flagged = [
            a
            for a in listed["assignments"]
            if a["id"] in (a1, a2) and a["countsTowardCertificate"]
        ]
        assert len(flagged) == 2

    def test_zero_flagged_assignments_save(self, harness: dict) -> None:
        aid = _create_publishable(harness, flag=False)
        got = harness["svc"].get_assignment(
            _COURSE, aid, cognito_sub=_TEACHER, role="teacher"
        )
        assert got["assignment"]["countsTowardCertificate"] is False


class TestModuleLockAndPurchase:
    def test_module2_locked_until_module1_quiz_passed(self, harness: dict) -> None:
        aid = _create_publishable(harness, module_id=_MOD2)
        harness["lock"].locked[_MOD2] = True
        with pytest.raises(Forbidden) as exc:
            harness["svc"].get_assignment(
                _COURSE, aid, cognito_sub=_STUDENT, role="student"
            )
        assert exc.value.code == "module_locked"

    def test_module2_own_quiz_not_required(self, harness: dict) -> None:
        """Earlier modules unlocked → module 2 assignment accessible (own quiz N/A)."""
        aid = _create_publishable(harness, module_id=_MOD2)
        harness["lock"].locked[_MOD2] = False
        got = harness["svc"].get_assignment(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        assert got["assignment"]["id"] == aid
        assert got["assignment"]["locked"] is False

    def test_purchase_required_403(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        harness["access"].allowed.clear()
        with pytest.raises(Forbidden) as exc:
            harness["svc"].get_assignment(
                _COURSE, aid, cognito_sub=_STUDENT, role="student"
            )
        assert exc.value.code == "purchase_required"


class TestResubmitMatrix:
    def _draft_with_ready_file(self, h: dict, aid: str) -> str:
        svc: AssignmentsService = h["svc"]
        storage: FakeStorage = h["storage"]
        opened = svc.open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        sid = opened["submission"]["id"]
        created = svc.create_submission_file(
            _COURSE,
            aid,
            sid,
            title="report",
            file_type="pdf",
            byte_size=100,
            cognito_sub=_STUDENT,
            role="student",
        )
        fid = created["fileId"]
        frow = h["repo"].files[fid]
        storage.objects[frow.object_key] = ObjectHead(
            content_type=frow.content_type, content_length=100
        )
        svc.complete_submission_file(
            _COURSE, aid, sid, fid, cognito_sub=_STUDENT, role="student"
        )
        return sid

    def test_draft_continues(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        first = harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        second = harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        assert first["submission"]["id"] == second["submission"]["id"]

    def test_submitted_returns_409(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        sid = self._draft_with_ready_file(harness, aid)
        harness["svc"].submit_submission(
            _COURSE, aid, sid, cognito_sub=_STUDENT, role="student", body={}
        )
        with pytest.raises(Conflict):
            harness["svc"].open_draft_submission(
                _COURSE, aid, cognito_sub=_STUDENT, role="student"
            )

    def test_passed_returns_409(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        sid = self._draft_with_ready_file(harness, aid)
        harness["svc"].submit_submission(
            _COURSE, aid, sid, cognito_sub=_STUDENT, role="student", body={}
        )
        assignment = harness["repo"].assignments[aid]
        scores = [
            {"criterionId": c.id, "points": c.max_points} for c in assignment.criteria
        ]
        harness["svc"].grade_submission(
            _COURSE,
            aid,
            sid,
            scores=scores,
            feedback="Excellent work overall.",
            cognito_sub=_TEACHER,
            role="teacher",
            body={"scores": scores, "feedback": "Excellent work overall."},
        )
        with pytest.raises(Conflict):
            harness["svc"].open_draft_submission(
                _COURSE, aid, cognito_sub=_STUDENT, role="student"
            )

    def test_failed_opens_new_draft(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        sid = self._draft_with_ready_file(harness, aid)
        harness["svc"].submit_submission(
            _COURSE, aid, sid, cognito_sub=_STUDENT, role="student", body={}
        )
        assignment = harness["repo"].assignments[aid]
        scores = [{"criterionId": c.id, "points": 0} for c in assignment.criteria]
        harness["svc"].grade_submission(
            _COURSE,
            aid,
            sid,
            scores=scores,
            feedback="Please revise and resubmit.",
            cognito_sub=_TEACHER,
            role="teacher",
            body={"scores": scores, "feedback": "Please revise and resubmit."},
        )
        opened = harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        assert opened["submission"]["id"] != sid
        assert opened["submission"]["status"] == "draft"


class TestScoring:
    def test_half_up_two_of_three_is_67(self) -> None:
        assert score_percent_half_up(awarded=2, max_total=3) == 67

    def test_sixty_nine_of_hundred_fails_pass_percent_70(self, harness: dict) -> None:
        svc: AssignmentsService = harness["svc"]
        created = svc.create_assignment(
            _COURSE,
            title="Score edge",
            module_id=_MOD1,
            pass_percent=70,
            cognito_sub=_TEACHER,
            role="teacher",
        )
        aid = created["assignment"]["id"]
        svc.update_assignment(
            _COURSE,
            aid,
            cognito_sub=_TEACHER,
            role="teacher",
            body={
                "instructions": {"mode": "plain", "text": "Score me"},
                "criteria": [{"label": "All", "maxPoints": 100}],
                "status": "published",
            },
        )
        # Manual submit path
        opened = svc.open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        sid = opened["submission"]["id"]
        created_f = svc.create_submission_file(
            _COURSE,
            aid,
            sid,
            title="f",
            file_type="pdf",
            byte_size=10,
            cognito_sub=_STUDENT,
            role="student",
        )
        frow = harness["repo"].files[created_f["fileId"]]
        harness["storage"].objects[frow.object_key] = ObjectHead(
            content_type=frow.content_type, content_length=10
        )
        svc.complete_submission_file(
            _COURSE,
            aid,
            sid,
            created_f["fileId"],
            cognito_sub=_STUDENT,
            role="student",
        )
        svc.submit_submission(
            _COURSE, aid, sid, cognito_sub=_STUDENT, role="student", body={}
        )
        cid = harness["repo"].assignments[aid].criteria[0].id
        result = svc.grade_submission(
            _COURSE,
            aid,
            sid,
            scores=[{"criterionId": cid, "points": 69}],
            feedback="Almost there, keep going.",
            cognito_sub=_TEACHER,
            role="teacher",
            body={
                "scores": [{"criterionId": cid, "points": 69}],
                "feedback": "Almost there, keep going.",
            },
        )
        assert result["scorePercent"] == 69
        assert result["passed"] is False

    def test_threshold_snapshot_ignores_later_pass_percent_edit(
        self, harness: dict
    ) -> None:
        svc: AssignmentsService = harness["svc"]
        aid = _create_publishable(harness)
        # Use single 100-pt criterion via replace
        svc.update_assignment(
            _COURSE,
            aid,
            cognito_sub=_TEACHER,
            role="teacher",
            body={
                "passPercent": 70,
                "criteria": [{"label": "All", "maxPoints": 100}],
            },
        )
        opened = svc.open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        sid = opened["submission"]["id"]
        created_f = svc.create_submission_file(
            _COURSE,
            aid,
            sid,
            title="f",
            file_type="pdf",
            byte_size=10,
            cognito_sub=_STUDENT,
            role="student",
        )
        frow = harness["repo"].files[created_f["fileId"]]
        harness["storage"].objects[frow.object_key] = ObjectHead(
            content_type=frow.content_type, content_length=10
        )
        svc.complete_submission_file(
            _COURSE,
            aid,
            sid,
            created_f["fileId"],
            cognito_sub=_STUDENT,
            role="student",
        )
        svc.submit_submission(
            _COURSE, aid, sid, cognito_sub=_STUDENT, role="student", body={}
        )
        cid = harness["repo"].assignments[aid].criteria[0].id
        result = svc.grade_submission(
            _COURSE,
            aid,
            sid,
            scores=[{"criterionId": cid, "points": 69}],
            feedback="Borderline score feedback.",
            cognito_sub=_TEACHER,
            role="teacher",
            body={
                "scores": [{"criterionId": cid, "points": 69}],
                "feedback": "Borderline score feedback.",
            },
        )
        assert result["passed"] is False
        svc.update_assignment(
            _COURSE,
            aid,
            cognito_sub=_TEACHER,
            role="teacher",
            body={"passPercent": 50},
        )
        got = svc.get_submission(
            _COURSE, aid, sid, cognito_sub=_STUDENT, role="student"
        )
        assert got["submission"]["grade"]["passed"] is False
        assert got["submission"]["grade"]["scorePercent"] == 69


class TestIdorAndListing:
    def test_other_student_submission_is_404(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        opened = harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        sid = opened["submission"]["id"]
        with pytest.raises(NotFound):
            harness["svc"].get_submission(
                _COURSE, aid, sid, cognito_sub=_OTHER, role="student"
            )

    def test_student_list_hides_other_rows(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_OTHER, role="student"
        )
        listed = harness["svc"].list_submissions(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        assert len(listed["submissions"]) == 1
        assert all("userSub" not in s for s in listed["submissions"])


class TestValidation:
    def test_unknown_json_key_400(self, harness: dict) -> None:
        with pytest.raises(BadRequest) as exc:
            harness["svc"].create_assignment(
                _COURSE,
                title="X",
                module_id=_MOD1,
                cognito_sub=_TEACHER,
                role="teacher",
                body={
                    "title": "X",
                    "moduleId": _MOD1,
                    "objectKey": "evil",
                },
            )
        assert "objectKey" in exc.value.message

    def test_title_crlf_rejected(self, harness: dict) -> None:
        with pytest.raises(BadRequest):
            harness["svc"].create_assignment(
                _COURSE,
                title="Bad\ntitle",
                module_id=_MOD1,
                cognito_sub=_TEACHER,
                role="teacher",
            )

    def test_rich_text_strips_script_and_onerror(self) -> None:
        cleaned = sanitize_rich_html(
            '<p>Hi</p><script>alert(1)</script><img src=x onerror="alert(1)">'
            '<a href="javascript:alert(1)">x</a><a href="https://ok.example">ok</a>'
        )
        assert "<script" not in cleaned.lower()
        assert "onerror" not in cleaned.lower()
        assert "javascript:" not in cleaned.lower()
        assert "<img" not in cleaned.lower()
        assert 'href="https://ok.example"' in cleaned

    def test_image_bytesize_52428801_rejected(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        with pytest.raises(BadRequest) as exc:
            harness["svc"].create_image_upload(
                _COURSE,
                aid,
                slot="instructions",
                content_type="image/png",
                byte_size=52_428_801,
                cognito_sub=_TEACHER,
                role="teacher",
                body={
                    "slot": "instructions",
                    "contentType": "image/png",
                    "byteSize": 52_428_801,
                },
            )
        assert exc.value.code == "invalid_byte_size"
        assert harness["storage"].put_calls == []

    def test_zip_file_type_rejected(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        opened = harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        sid = opened["submission"]["id"]
        with pytest.raises(BadRequest) as exc:
            harness["svc"].create_submission_file(
                _COURSE,
                aid,
                sid,
                title="archive",
                file_type="zip",
                byte_size=100,
                cognito_sub=_STUDENT,
                role="student",
                body={"title": "archive", "fileType": "zip", "byteSize": 100},
            )
        assert exc.value.code == "invalid_file_type"
        assert harness["storage"].put_calls == []


class TestGradeImmutable:
    def test_grade_immutable_second_call_409(self, harness: dict) -> None:
        aid = _create_publishable(harness)
        opened = harness["svc"].open_draft_submission(
            _COURSE, aid, cognito_sub=_STUDENT, role="student"
        )
        sid = opened["submission"]["id"]
        created_f = harness["svc"].create_submission_file(
            _COURSE,
            aid,
            sid,
            title="f",
            file_type="pdf",
            byte_size=10,
            cognito_sub=_STUDENT,
            role="student",
        )
        frow = harness["repo"].files[created_f["fileId"]]
        harness["storage"].objects[frow.object_key] = ObjectHead(
            content_type=frow.content_type, content_length=10
        )
        harness["svc"].complete_submission_file(
            _COURSE,
            aid,
            sid,
            created_f["fileId"],
            cognito_sub=_STUDENT,
            role="student",
        )
        harness["svc"].submit_submission(
            _COURSE, aid, sid, cognito_sub=_STUDENT, role="student", body={}
        )
        criteria = harness["repo"].assignments[aid].criteria
        scores = [{"criterionId": c.id, "points": 1} for c in criteria]
        harness["svc"].grade_submission(
            _COURSE,
            aid,
            sid,
            scores=scores,
            feedback="First grade feedback text.",
            cognito_sub=_TEACHER,
            role="teacher",
            body={"scores": scores, "feedback": "First grade feedback text."},
        )
        with pytest.raises(Conflict) as exc:
            harness["svc"].grade_submission(
                _COURSE,
                aid,
                sid,
                scores=scores,
                feedback="Second grade feedback text.",
                cognito_sub=_TEACHER,
                role="teacher",
                body={"scores": scores, "feedback": "Second grade feedback text."},
            )
        assert exc.value.code == "grade_immutable"
        assert len(harness["mail"].messages) == 1
