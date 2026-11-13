"""DSQL-3 S3: course delete registry, tombstone, purchases, authz."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.common.errors import Conflict, NotFound
from services.course_deletion.catalog import register_catalog_steps
from services.course_deletion.registry import CourseDeletionRegistry
from services.course_deletion.runner import CourseDeletionRunner
from services.course_management.models import Course
from services.course_management.service import CourseManagementService


_VID = "11111111-1111-4111-8111-111111111111"
_OWNER = "teacher-sub"


def _course(*, status: str = "DRAFT") -> Course:
    return Course(
        id=_VID,
        title="T",
        description="",
        status=status,
        createdBy=_OWNER,
        thumbnailKey="",
    )


@pytest.fixture
def repo() -> MagicMock:
    m = MagicMock()
    m.course_has_purchase.return_value = False
    return m


@pytest.fixture
def deletion_runner() -> MagicMock:
    return MagicMock(spec=CourseDeletionRunner)


@pytest.fixture
def svc(repo: MagicMock, deletion_runner: MagicMock) -> CourseManagementService:
    course_access = MagicMock()
    return CourseManagementService(
        repo,
        None,
        course_access=course_access,
        media_cleanup_queue_url="https://sqs.example/queue",
        deletion_runner=deletion_runner,
    )


class TestDeleteCourseDsql:
    @patch("services.course_management.service.send_media_cleanup_job")
    def test_purchase_blocks_delete_before_tombstone(
        self,
        _send: MagicMock,
        svc: CourseManagementService,
        repo: MagicMock,
        deletion_runner: MagicMock,
    ) -> None:
        repo.get_course.return_value = _course()
        repo.course_has_purchase.return_value = True
        repo.list_lessons.return_value = []

        with pytest.raises(Conflict):
            svc.delete_course(_VID)

        repo.set_course_status.assert_not_called()
        deletion_runner.run.assert_not_called()
        _send.assert_not_called()

    @patch("services.course_management.service.send_media_cleanup_job")
    def test_no_purchase_sets_deleting_runs_runner_then_enqueue(
        self,
        send_job: MagicMock,
        svc: CourseManagementService,
        repo: MagicMock,
        deletion_runner: MagicMock,
    ) -> None:
        repo.get_course.return_value = _course()
        repo.list_lessons.return_value = []
        repo.list_lesson_file_object_keys_for_course.return_value = []
        order: list[str] = []

        def _mark_status(*_a: object, **_k: object) -> None:
            order.append("tombstone")

        def _mark_run(*_a: object, **_k: object) -> None:
            order.append("runner")

        def _mark_send(*_a: object, **_k: object) -> None:
            order.append("sqs")

        repo.set_course_status.side_effect = _mark_status
        deletion_runner.run.side_effect = _mark_run
        send_job.side_effect = _mark_send

        svc.delete_course(_VID)

        repo.set_course_status.assert_called_once_with(_VID, "deleting")
        deletion_runner.run.assert_called_once_with("course", _VID)
        assert order == ["tombstone", "runner"]

    def test_include_deleting_authz_sees_tombstone(
        self, svc: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(status="deleting")
        svc.ensure_can_modify_course(
            _VID,
            cognito_sub=_OWNER,
            role="teacher",
            include_deleting=True,
        )
        repo.get_course.assert_called_once_with(_VID, include_deleting=True)

    def test_publish_deleting_course_is_not_found(
        self, svc: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = None
        with pytest.raises(NotFound, match="Course not found"):
            svc.publish_course(_VID)


class TestRegisterCatalogSteps:
    def test_course_scope_parent_row_runs_last(self) -> None:
        repo = MagicMock()
        log: list[str] = []

        def _log(name: str):
            def _run(_: str) -> None:
                log.append(name)

            return _run

        for method, name in (
            ("delete_lesson_files_for_course", "files"),
            ("delete_lessons_for_course", "lessons"),
            ("delete_course_modules_for_course", "modules"),
            ("delete_course_row", "course_row"),
        ):
            getattr(repo, method).side_effect = _log(name)

        registry = CourseDeletionRegistry()
        register_catalog_steps(registry, repo)
        CourseDeletionRunner(registry).run("course", _VID)
        assert log == ["files", "lessons", "modules", "course_row"]
