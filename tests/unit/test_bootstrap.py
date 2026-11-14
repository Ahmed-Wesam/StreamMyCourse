"""Unit tests for `bootstrap.lambda_bootstrap` (the Lambda's composition root)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import bootstrap as bootstrap_mod
import services.course_management.image_storage as image_storage_mod
import services.course_management.storage as storage_mod
from config import AppConfig


@pytest.fixture(autouse=True)
def _clear_module_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """The bootstrap module memoizes deps in a module-level dict. Clear it so
    each test starts from a cold cache."""
    monkeypatch.setattr(bootstrap_mod, "_cached", {})


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "VIDEO_BUCKET",
        "DEFAULT_MP4_URL",
        "VIDEO_URL",
        "ALLOWED_ORIGINS",
        "DSQL_ENDPOINT",
        "DB_HOST",
        "DB_NAME",
        "DB_SECRET_ARN",
        "PROGRESS_COMPLETE_RATIO",
        "PROGRESS_POSITION_SLACK_SEC",
        "RATE_LIMIT_MAX_OVERRIDES",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def mocked_storage(monkeypatch: pytest.MonkeyPatch):
    """Patch S3 client factory so media storage construction stays hermetic."""
    mock_s3 = MagicMock()
    monkeypatch.setattr(storage_mod, "_s3_client", lambda: mock_s3)
    monkeypatch.setattr(image_storage_mod, "_s3_client", lambda: mock_s3)
    import services.assignments.storage as assignment_storage_mod

    monkeypatch.setattr(assignment_storage_mod, "_s3_client", lambda: mock_s3)


def _dsql_cfg(
    *,
    video_bucket: str = "",
    dsql_endpoint: str = "abc.dsql.eu-west-1.on.aws",
) -> AppConfig:
    return AppConfig(
        video_bucket=video_bucket,
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
        dsql_endpoint=dsql_endpoint,
    )


@pytest.fixture
def _mocked_dsql(monkeypatch: pytest.MonkeyPatch):
    """Patch the DSQL connection factory so bootstrap can wire repos without Aurora."""
    fake_factory = lambda: MagicMock(name="dsql-connection")
    monkeypatch.setattr(
        bootstrap_mod,
        "_build_dsql_connection_factory",
        lambda cfg: fake_factory,
    )
    return fake_factory


class TestLambdaBootstrap:
    def test_returns_none_service_when_dsql_env_incomplete(self) -> None:
        (
            cfg,
            service,
            auth_service,
            auth_repo,
            progress_service,
            question_bank_service,
            purchase_manage_service,
            rate_limit_service,
        ) = bootstrap_mod.lambda_bootstrap()
        assert isinstance(cfg, AppConfig)
        assert service is None
        assert auth_service is None
        assert auth_repo is None
        assert progress_service is None
        assert question_bank_service is None
        assert purchase_manage_service is None
        assert rate_limit_service is None

    def test_warm_cache_returns_same_service_instance(
        self, monkeypatch: pytest.MonkeyPatch, mocked_storage, _mocked_dsql
    ) -> None:
        monkeypatch.setenv("DSQL_ENDPOINT", "abc.dsql.eu-west-1.on.aws")
        monkeypatch.setenv("VIDEO_BUCKET", "my-bucket")

        _cfg1, svc1, auth1, repo1, prog1, qb1, purchase_manage1, rl1 = (
            bootstrap_mod.lambda_bootstrap()
        )
        _cfg2, svc2, auth2, repo2, prog2, qb2, purchase_manage2, rl2 = (
            bootstrap_mod.lambda_bootstrap()
        )

        assert svc1 is not None
        assert svc2 is not None
        assert svc1 is svc2
        assert auth1 is auth2
        assert repo1 is repo2
        assert prog1 is prog2
        assert qb1 is qb2
        assert purchase_manage1 is purchase_manage2
        assert rl1 is rl2

    def test_dsql_complete_builds_progress_service(
        self, monkeypatch: pytest.MonkeyPatch, mocked_storage, _mocked_dsql
    ) -> None:
        monkeypatch.setenv("DSQL_ENDPOINT", "abc.dsql.eu-west-1.on.aws")
        (
            _cfg,
            service,
            auth_service,
            auth_repo,
            progress_service,
            question_bank_service,
            purchase_manage_service,
            rate_limit_service,
        ) = bootstrap_mod.lambda_bootstrap()
        assert service is not None
        assert auth_service is not None
        assert auth_repo is not None
        assert progress_service is not None
        assert question_bank_service is not None
        assert purchase_manage_service is not None
        assert rate_limit_service is not None


class TestBuildAwsDeps:
    def test_raises_when_dsql_incomplete(self) -> None:
        empty_cfg = AppConfig(
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
        )
        with pytest.raises(RuntimeError, match="DSQL_ENDPOINT"):
            bootstrap_mod.build_aws_deps(empty_cfg)

    def test_constructs_aws_deps_with_dsql(self, mocked_storage, _mocked_dsql) -> None:
        cfg = _dsql_cfg(video_bucket="b")
        deps = bootstrap_mod.build_aws_deps(cfg)
        assert deps.cfg is cfg
        assert deps.service is not None
        assert deps.auth_service is not None
        assert deps.auth_repo is not None
        assert deps.progress_service is not None
        assert deps.question_bank_service is not None
        assert deps.purchase_manage_service is not None
        assert deps.rate_limit_service is not None
        assert deps.lesson_notes_service is not None
        assert deps.assignments_service is not None

    def test_course_management_receives_assignment_media_keys_lister(
        self, mocked_storage, _mocked_dsql
    ) -> None:
        """RS-13: bootstrap must pass the real assignments key lister into course delete."""
        cfg = _dsql_cfg(video_bucket="b")
        deps = bootstrap_mod.build_aws_deps(cfg)
        lister = getattr(deps.service, "_assignment_media_keys", None)
        assert lister is not None
        assert hasattr(lister, "list_object_keys_for_course")
        # Same object used by AssignmentsService repo (AssignmentsRdsRepository).
        assert lister is deps.assignments_service._repo

    def test_course_management_wires_deletion_runner(self, mocked_storage, _mocked_dsql) -> None:
        """DSQL-3: bootstrap registers catalog steps on the course deletion runner."""
        cfg = _dsql_cfg(video_bucket="b")
        deps = bootstrap_mod.build_aws_deps(cfg)
        runner = getattr(deps.service, "_deletion_runner", None)
        assert runner is not None
        course_steps = runner._registry.ordered_steps("course")
        assert [s.order for s in course_steps] == [100, 100, 300, 400, 900, 900, 900, 1000]
        assert [s.name for s in course_steps[:4]] == [
            "lesson_progress_course",
            "lesson_notes_course",
            "quiz_rows_course",
            "assignment_rows_course",
        ]
        assert course_steps[-1].name == "course_row"


class TestWarmAwsDepsIfNeeded:
    def test_noop_without_dsql_config(self) -> None:
        cfg = AppConfig(
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
        )
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert bootstrap_mod._cached == {}

    def test_populates_cache_when_dsql_complete(self, mocked_storage, _mocked_dsql) -> None:
        cfg = _dsql_cfg(video_bucket="b")
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert "aws" in bootstrap_mod._cached

    def test_subsequent_call_does_not_rebuild(self, mocked_storage, _mocked_dsql) -> None:
        cfg = _dsql_cfg()
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        first = bootstrap_mod._cached["aws"]
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert bootstrap_mod._cached["aws"] is first


class TestGetCachedAwsDeps:
    def test_empty_cache_returns_none(self) -> None:
        assert bootstrap_mod.get_cached_aws_deps() is None

    def test_returns_cached_when_set(self, monkeypatch: pytest.MonkeyPatch, mocked_storage, _mocked_dsql) -> None:
        cfg = _dsql_cfg()
        deps = bootstrap_mod.build_aws_deps(cfg)
        monkeypatch.setattr(bootstrap_mod, "_cached", {"aws": deps})
        assert bootstrap_mod.get_cached_aws_deps() is deps


class TestBuildAwsDepsWiresRdsRepos:
    def test_wires_rds_repos(self, _mocked_dsql) -> None:
        from services.auth.rds_repo import UserProfileRdsRepository
        from services.course_management.rds_repo import CourseCatalogRdsRepository
        from services.progress.rds_repo import LessonProgressRdsRepository
        from services.question_banks.rds_repo import QuestionBankRdsRepository
        from services.rate_limit.rds_repo import RateLimitRdsRepository
        from services.rate_limit.service import RateLimitService
        from services.purchases.repo import PurchaseRdsRepository
        from services.purchases.service import CourseAccessService

        cfg = _dsql_cfg()
        deps = bootstrap_mod.build_aws_deps(cfg)
        assert isinstance(deps.service._repo, CourseCatalogRdsRepository)
        assert isinstance(deps.service._course_access, CourseAccessService)
        assert isinstance(
            deps.service._course_access._purchase_repo,
            PurchaseRdsRepository,
        )
        assert isinstance(deps.auth_service._repo, UserProfileRdsRepository)
        assert deps.auth_repo is deps.auth_service._repo
        assert isinstance(deps.progress_service._progress_repo, LessonProgressRdsRepository)
        assert isinstance(deps.question_bank_service._repo, QuestionBankRdsRepository)
        assert deps.service._module_quiz_visibility is not None
        assert isinstance(deps.rate_limit_service, RateLimitService)
        assert isinstance(deps.rate_limit_service._repo, RateLimitRdsRepository)


class TestModuleQuizVisibilityAdapter:
    def test_skips_rds_when_course_draft(self) -> None:
        mock_repo = MagicMock()
        adapter = bootstrap_mod._ModuleQuizVisibilityAdapter(mock_repo)
        result = adapter.module_quiz_visibility_by_course(
            "course-id",
            course_status="DRAFT",
            has_lesson_access=True,
            cognito_sub="student-sub",
        )
        assert result == {}
        mock_repo.list_module_quiz_visibility_for_course.assert_not_called()

    def test_skips_rds_when_no_lesson_access(self) -> None:
        mock_repo = MagicMock()
        adapter = bootstrap_mod._ModuleQuizVisibilityAdapter(mock_repo)
        result = adapter.module_quiz_visibility_by_course(
            "course-id",
            course_status="PUBLISHED",
            has_lesson_access=False,
            cognito_sub="student-sub",
        )
        assert result == {}
        mock_repo.list_module_quiz_visibility_for_course.assert_not_called()

    def test_queries_rds_when_published_and_has_access(self) -> None:
        mock_repo = MagicMock()
        mock_repo.list_module_quiz_visibility_for_course.return_value = {
            "m1": {"servedCountN": 2},
        }
        mock_repo.list_module_quiz_pass_percent_for_course.return_value = {"m1": 70}
        mock_repo.list_submitted_attempt_scores_by_module.return_value = {}
        mock_repo.list_latest_submission_scores_for_course.return_value = {}
        adapter = bootstrap_mod._ModuleQuizVisibilityAdapter(mock_repo)
        result = adapter.module_quiz_visibility_by_course(
            "course-id",
            course_status="PUBLISHED",
            has_lesson_access=True,
            cognito_sub="student-sub",
        )
        mock_repo.list_module_quiz_visibility_for_course.assert_called_once_with(
            course_id="course-id"
        )
        mock_repo.list_latest_submission_scores_for_course.assert_called_once_with(
            course_id="course-id",
            user_sub="student-sub",
        )
        assert result == {
            "m1": {
                "available": True,
                "servedCountN": 2,
                "passPercent": 70,
                "passed": False,
            },
        }

    def test_includes_latest_score_percent_when_submission_exists(self) -> None:
        mock_repo = MagicMock()
        mock_repo.list_module_quiz_visibility_for_course.return_value = {
            "m1": {"servedCountN": 3},
        }
        mock_repo.list_module_quiz_pass_percent_for_course.return_value = {"m1": 70}
        mock_repo.list_submitted_attempt_scores_by_module.return_value = {
            "m1": [{"correctCount": 2, "totalCount": 3}],
        }
        mock_repo.list_latest_submission_scores_for_course.return_value = {
            "m1": {"correctCount": 2, "totalCount": 3},
        }
        adapter = bootstrap_mod._ModuleQuizVisibilityAdapter(mock_repo)
        result = adapter.module_quiz_visibility_by_course(
            "course-id",
            course_status="PUBLISHED",
            has_lesson_access=True,
            cognito_sub="student-sub",
        )
        assert result == {
            "m1": {
                "available": True,
                "servedCountN": 3,
                "passPercent": 70,
                "passed": False,
                "latestScorePercent": 67,
            },
        }


class TestDsqlConnectionFactory:
    def test_raises_when_dsql_endpoint_missing(self) -> None:
        cfg = _dsql_cfg(dsql_endpoint="")
        with pytest.raises(RuntimeError, match="DSQL_ENDPOINT"):
            bootstrap_mod._build_dsql_connection_factory(cfg)
