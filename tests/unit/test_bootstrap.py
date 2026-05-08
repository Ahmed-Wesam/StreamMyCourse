"""Unit tests for `bootstrap.lambda_bootstrap` (the Lambda's composition root)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import bootstrap as bootstrap_mod
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
        "COGNITO_AUTH_ENABLED",
        "DB_HOST",
        "DB_NAME",
        "DB_PORT",
        "DB_SECRET_ARN",
        "PROGRESS_COMPLETE_RATIO",
        "PROGRESS_POSITION_SLACK_SEC",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def mocked_storage(monkeypatch: pytest.MonkeyPatch):
    """Patch S3 client factory so `CourseMediaStorage` construction stays hermetic."""
    monkeypatch.setattr(storage_mod, "_s3_client", lambda: MagicMock())


def _rds_cfg(
    *,
    video_bucket: str = "",
    db_host: str = "rds.example.com",
    db_name: str = "smc",
    db_secret_arn: str = "arn:aws:secretsmanager:eu-west-1:123:secret:rds-cred-abcdef",
) -> AppConfig:
    return AppConfig(
        video_bucket=video_bucket,
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
        cognito_auth_enabled=False,
        db_host=db_host,
        db_name=db_name,
        db_port=5432,
        db_secret_arn=db_secret_arn,
    )


@pytest.fixture
def _mocked_rds(monkeypatch: pytest.MonkeyPatch):
    """Patch the RDS connection factory so bootstrap can wire repos without Secrets Manager."""
    fake_factory = lambda: MagicMock(name="psycopg2-connection")
    monkeypatch.setattr(bootstrap_mod, "_build_rds_connection_factory", lambda cfg: fake_factory)
    return fake_factory


class TestLambdaBootstrap:
    def test_returns_none_service_when_rds_env_incomplete(self) -> None:
        cfg, service, auth_service, progress_service = bootstrap_mod.lambda_bootstrap()
        assert isinstance(cfg, AppConfig)
        assert service is None
        assert auth_service is None
        assert progress_service is None

    def test_warm_cache_returns_same_service_instance(
        self, monkeypatch: pytest.MonkeyPatch, mocked_storage, _mocked_rds
    ) -> None:
        monkeypatch.setenv("DB_HOST", "rds.example.com")
        monkeypatch.setenv("DB_NAME", "smc")
        monkeypatch.setenv(
            "DB_SECRET_ARN",
            "arn:aws:secretsmanager:eu-west-1:123:secret:rds-cred-abcdef",
        )
        monkeypatch.setenv("VIDEO_BUCKET", "my-bucket")

        _cfg1, svc1, auth1, prog1 = bootstrap_mod.lambda_bootstrap()
        _cfg2, svc2, auth2, prog2 = bootstrap_mod.lambda_bootstrap()

        assert svc1 is not None
        assert svc2 is not None
        assert svc1 is svc2
        assert auth1 is auth2
        assert prog1 is prog2

    def test_rds_complete_builds_progress_service(
        self, monkeypatch: pytest.MonkeyPatch, mocked_storage, _mocked_rds
    ) -> None:
        monkeypatch.setenv("DB_HOST", "rds.example.com")
        monkeypatch.setenv("DB_NAME", "smc")
        monkeypatch.setenv(
            "DB_SECRET_ARN",
            "arn:aws:secretsmanager:eu-west-1:123:secret:rds-cred-abcdef",
        )
        _cfg, service, auth_service, progress_service = bootstrap_mod.lambda_bootstrap()
        assert service is not None
        assert auth_service is not None
        assert progress_service is not None


class TestBuildAwsDeps:
    def test_raises_when_rds_incomplete(self) -> None:
        empty_cfg = AppConfig(
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        with pytest.raises(RuntimeError, match="RDS catalog requires"):
            bootstrap_mod.build_aws_deps(empty_cfg)

    def test_constructs_aws_deps_with_rds(self, mocked_storage, _mocked_rds) -> None:
        cfg = _rds_cfg(video_bucket="b")
        deps = bootstrap_mod.build_aws_deps(cfg)
        assert deps.cfg is cfg
        assert deps.service is not None
        assert deps.auth_service is not None
        assert deps.progress_service is not None


class TestWarmAwsDepsIfNeeded:
    def test_noop_without_rds_config(self) -> None:
        cfg = AppConfig(
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert bootstrap_mod._cached == {}

    def test_populates_cache_when_rds_complete(self, mocked_storage, _mocked_rds) -> None:
        cfg = _rds_cfg(video_bucket="b")
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert "aws" in bootstrap_mod._cached

    def test_subsequent_call_does_not_rebuild(self, mocked_storage, _mocked_rds) -> None:
        cfg = _rds_cfg()
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        first = bootstrap_mod._cached["aws"]
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert bootstrap_mod._cached["aws"] is first


class TestGetCachedAwsDeps:
    def test_empty_cache_returns_none(self) -> None:
        assert bootstrap_mod.get_cached_aws_deps() is None

    def test_returns_cached_when_set(self, monkeypatch: pytest.MonkeyPatch, mocked_storage, _mocked_rds) -> None:
        cfg = _rds_cfg()
        deps = bootstrap_mod.build_aws_deps(cfg)
        monkeypatch.setattr(bootstrap_mod, "_cached", {"aws": deps})
        assert bootstrap_mod.get_cached_aws_deps() is deps


class TestBuildAwsDepsWiresRdsRepos:
    def test_wires_rds_repos(self, _mocked_rds) -> None:
        from services.auth.rds_repo import UserProfileRdsRepository
        from services.course_management.rds_repo import CourseCatalogRdsRepository
        from services.enrollment.rds_repo import EnrollmentRdsRepository
        from services.progress.rds_repo import LessonProgressRdsRepository

        cfg = _rds_cfg()
        deps = bootstrap_mod.build_aws_deps(cfg)
        assert isinstance(deps.service._repo, CourseCatalogRdsRepository)
        assert isinstance(deps.service._enrollments, EnrollmentRdsRepository)
        assert isinstance(deps.auth_service._repo, UserProfileRdsRepository)
        assert isinstance(deps.progress_service._progress_repo, LessonProgressRdsRepository)


class TestRdsConnectionFactory:
    """`_build_rds_connection_factory` is the single place Secrets Manager and
    psycopg2.connect are called. Keep it testable in isolation."""

    def test_raises_when_db_secret_arn_missing(self) -> None:
        cfg = _rds_cfg(db_secret_arn="")
        with pytest.raises(RuntimeError, match="DB_SECRET_ARN"):
            bootstrap_mod._build_rds_connection_factory(cfg)

    def test_raises_when_db_host_missing(self) -> None:
        cfg = _rds_cfg(db_host="")
        with pytest.raises(RuntimeError, match="DB_HOST"):
            bootstrap_mod._build_rds_connection_factory(cfg)

    def test_raises_when_db_name_missing(self) -> None:
        cfg = _rds_cfg(db_name="")
        with pytest.raises(RuntimeError, match="DB_NAME"):
            bootstrap_mod._build_rds_connection_factory(cfg)

    def test_factory_reads_secret_and_calls_psycopg2_connect(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import json

        secret_payload = json.dumps({"username": "smc_app", "password": "hunter2"})
        fake_sm = MagicMock()
        fake_sm.get_secret_value.return_value = {"SecretString": secret_payload}
        fake_boto3_client = MagicMock(return_value=fake_sm)
        monkeypatch.setattr(bootstrap_mod, "_secretsmanager_client", fake_boto3_client)

        fake_connect = MagicMock(name="psycopg2.connect")
        monkeypatch.setattr(bootstrap_mod, "_psycopg2_connect", fake_connect)

        cfg = _rds_cfg()
        factory = bootstrap_mod._build_rds_connection_factory(cfg)
        fake_sm.get_secret_value.assert_not_called()
        conn = factory()
        assert conn is fake_connect.return_value
        fake_sm.get_secret_value.assert_called_once()
        args, kwargs = fake_sm.get_secret_value.call_args
        assert kwargs.get("SecretId") == cfg.db_secret_arn or cfg.db_secret_arn in args
        _, connect_kwargs = fake_connect.call_args
        assert connect_kwargs.get("sslmode") == "require"
        assert connect_kwargs.get("host") == "rds.example.com"
        assert connect_kwargs.get("port") == 5432
        assert connect_kwargs.get("dbname") == "smc"
        assert connect_kwargs.get("user") == "smc_app"
        assert connect_kwargs.get("password") == "hunter2"

    def test_psycopg2_connect_sets_autocommit_true_on_connection(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The connection factory must enable autocommit on every fresh
        connection so read-only queries do not leave the warm Lambda
        container's connection idle in a transaction holding share locks
        across invocations. This is the application-level half of the fix
        for the deploy-blocking AccessExclusiveLock contention seen during
        migration 003 rollouts; the RDS-level half is the
        idle_in_transaction_session_timeout parameter group in
        infrastructure/templates/rds-stack.yaml."""
        import psycopg2 as psycopg2_mod

        fake_conn = MagicMock(name="conn")
        fake_psycopg2_connect = MagicMock(return_value=fake_conn)
        monkeypatch.setattr(psycopg2_mod, "connect", fake_psycopg2_connect)

        out = bootstrap_mod._psycopg2_connect(host="h", port=5432, dbname="d", user="u", password="p")

        assert out is fake_conn
        # autocommit was set to True on the returned connection (not just on
        # any random connection — this exact one).
        assert fake_conn.autocommit is True
        fake_psycopg2_connect.assert_called_once()
