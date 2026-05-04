"""Unit tests for `bootstrap.lambda_bootstrap` (the Lambda's composition root)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import bootstrap as bootstrap_mod
import services.auth.repo as auth_repo_mod
import services.course_management.repo as repo_mod
import services.course_management.storage as storage_mod
import services.enrollment.repo as enrollment_repo_mod
from config import AppConfig


@pytest.fixture(autouse=True)
def _clear_module_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """The bootstrap module memoizes deps in a module-level dict. Clear it so
    each test starts from a cold cache."""
    monkeypatch.setattr(bootstrap_mod, "_cached", {})


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "TABLE_NAME",
        "VIDEO_BUCKET",
        "DEFAULT_MP4_URL",
        "VIDEO_URL",
        "ALLOWED_ORIGINS",
        "COGNITO_AUTH_ENABLED",
        "USE_RDS",
        "DB_HOST",
        "DB_NAME",
        "DB_PORT",
        "DB_SECRET_ARN",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def mocked_aws(monkeypatch: pytest.MonkeyPatch):
    """Patch the boto3 boundary so build_aws_deps() is hermetic."""
    monkeypatch.setattr(repo_mod, "boto3", MagicMock())
    monkeypatch.setattr(auth_repo_mod, "boto3", MagicMock())
    monkeypatch.setattr(enrollment_repo_mod, "boto3", MagicMock())
    monkeypatch.setattr(repo_mod, "Attr", MagicMock())
    monkeypatch.setattr(repo_mod, "Key", MagicMock())
    monkeypatch.setattr(storage_mod, "_s3_client", lambda: MagicMock())


class TestLambdaBootstrap:
    def test_returns_none_service_when_table_name_unset(self) -> None:
        cfg, service, auth_service = bootstrap_mod.lambda_bootstrap()
        assert isinstance(cfg, AppConfig)
        assert cfg.table_name == ""
        assert service is None
        assert auth_service is None

    def test_warm_cache_returns_same_service_instance(
        self, monkeypatch: pytest.MonkeyPatch, mocked_aws
    ) -> None:
        monkeypatch.setenv("TABLE_NAME", "my-table")
        monkeypatch.setenv("VIDEO_BUCKET", "my-bucket")

        _cfg1, svc1, auth1 = bootstrap_mod.lambda_bootstrap()
        _cfg2, svc2, auth2 = bootstrap_mod.lambda_bootstrap()

        assert svc1 is not None
        assert svc2 is not None
        assert svc1 is svc2
        assert auth1 is auth2

    def test_table_set_but_no_bucket_still_builds_service(
        self, monkeypatch: pytest.MonkeyPatch, mocked_aws
    ) -> None:
        # No VIDEO_BUCKET → storage is None inside the service, but the
        # service itself still constructs successfully.
        monkeypatch.setenv("TABLE_NAME", "my-table")

        _cfg, service, auth_service = bootstrap_mod.lambda_bootstrap()
        assert service is not None
        assert auth_service is not None


class TestBuildAwsDeps:
    def test_empty_table_name_in_cfg_raises(self) -> None:
        empty_cfg = AppConfig(
            table_name="",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        with pytest.raises(RuntimeError, match="TABLE_NAME"):
            bootstrap_mod.build_aws_deps(empty_cfg)

    def test_constructs_aws_deps_with_table_and_bucket(self, mocked_aws) -> None:
        cfg = AppConfig(
            table_name="t",
            video_bucket="b",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        deps = bootstrap_mod.build_aws_deps(cfg)
        assert deps.cfg is cfg
        assert deps.service is not None
        assert deps.auth_service is not None


class TestWarmAwsDepsIfNeeded:
    def test_noop_without_table_name(self) -> None:
        cfg = AppConfig(
            table_name="",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert bootstrap_mod._cached == {}

    def test_populates_cache_when_table_name_set(self, mocked_aws) -> None:
        cfg = AppConfig(
            table_name="t",
            video_bucket="b",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert "aws" in bootstrap_mod._cached

    def test_subsequent_call_does_not_rebuild(self, mocked_aws) -> None:
        cfg = AppConfig(
            table_name="t",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        first = bootstrap_mod._cached["aws"]
        bootstrap_mod.warm_aws_deps_if_needed(cfg)
        assert bootstrap_mod._cached["aws"] is first


class TestGetCachedAwsDeps:
    def test_empty_cache_returns_none(self) -> None:
        assert bootstrap_mod.get_cached_aws_deps() is None

    def test_returns_cached_when_set(
        self, monkeypatch: pytest.MonkeyPatch, mocked_aws
    ) -> None:
        cfg = AppConfig(
            table_name="t",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
        )
        deps = bootstrap_mod.build_aws_deps(cfg)
        monkeypatch.setattr(bootstrap_mod, "_cached", {"aws": deps})
        assert bootstrap_mod.get_cached_aws_deps() is deps


@pytest.fixture
def _mocked_rds(monkeypatch: pytest.MonkeyPatch):
    """Patch the RDS connection factory so the bootstrap can wire the RDS
    repos without hitting Secrets Manager or a real PostgreSQL instance."""
    # Replace the private factory builder with a no-op that returns a MagicMock
    # callable. The repos call it lazily (on first query), so they accept any
    # object that satisfies the connection protocol.
    fake_factory = lambda: MagicMock(name="psycopg2-connection")
    monkeypatch.setattr(bootstrap_mod, "_build_rds_connection_factory", lambda cfg: fake_factory)
    return fake_factory


class TestBuildAwsDepsWithRds:
    """When ``cfg.use_rds`` is True the bootstrap wires PostgreSQL adapters in
    place of the DynamoDB ones. Service and controller layers stay untouched."""

    def test_use_rds_true_wires_rds_repos(
        self, monkeypatch: pytest.MonkeyPatch, _mocked_rds
    ) -> None:
        from services.auth.rds_repo import UserProfileRdsRepository
        from services.course_management.rds_repo import CourseCatalogRdsRepository
        from services.enrollment.rds_repo import EnrollmentRdsRepository

        cfg = AppConfig(
            table_name="t",  # retained during rollout; not used by RDS repos
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
            use_rds=True,
            db_host="rds.example.com",
            db_name="smc",
            db_port=5432,
            db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:rds-cred-abcdef",
        )
        deps = bootstrap_mod.build_aws_deps(cfg)
        # The service holds a private ``_repo``; inspect the concrete type to
        # prove the RDS adapter was injected.
        assert isinstance(deps.service._repo, CourseCatalogRdsRepository)
        assert isinstance(deps.service._enrollments, EnrollmentRdsRepository)
        assert isinstance(deps.auth_service._repo, UserProfileRdsRepository)

    def test_use_rds_false_still_wires_dynamo_repos(self, mocked_aws) -> None:
        from services.auth.repo import UserProfileRepository
        from services.course_management.repo import CourseCatalogRepository
        from services.enrollment.repo import EnrollmentRepository

        cfg = AppConfig(
            table_name="t",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
            use_rds=False,
        )
        deps = bootstrap_mod.build_aws_deps(cfg)
        assert isinstance(deps.service._repo, CourseCatalogRepository)
        assert isinstance(deps.service._enrollments, EnrollmentRepository)
        assert isinstance(deps.auth_service._repo, UserProfileRepository)

    def test_use_rds_true_does_not_require_table_name(
        self, monkeypatch: pytest.MonkeyPatch, _mocked_rds
    ) -> None:
        # Once cutover is complete the DynamoDB table can be removed; the
        # bootstrap must not insist on TABLE_NAME when the RDS path is active.
        cfg = AppConfig(
            table_name="",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
            use_rds=True,
            db_host="rds.example.com",
            db_name="smc",
            db_port=5432,
            db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:rds-cred-abcdef",
        )
        # Must not raise.
        deps = bootstrap_mod.build_aws_deps(cfg)
        assert deps.service is not None
        assert deps.auth_service is not None


class TestRdsConnectionFactory:
    """`_build_rds_connection_factory` is the single place Secrets Manager and
    psycopg2.connect are called. Keep it testable in isolation."""

    def test_raises_when_db_secret_arn_missing(self) -> None:
        cfg = AppConfig(
            table_name="",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
            use_rds=True,
            db_host="rds.example.com",
            db_name="smc",
            db_port=5432,
            db_secret_arn="",  # unset
        )
        with pytest.raises(RuntimeError, match="DB_SECRET_ARN"):
            bootstrap_mod._build_rds_connection_factory(cfg)

    def test_raises_when_db_host_missing(self) -> None:
        cfg = AppConfig(
            table_name="",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
            use_rds=True,
            db_host="",
            db_name="smc",
            db_port=5432,
            db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:x-abcdef",
        )
        with pytest.raises(RuntimeError, match="DB_HOST"):
            bootstrap_mod._build_rds_connection_factory(cfg)

    def test_factory_reads_secret_and_calls_psycopg2_connect(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The factory must fetch credentials from Secrets Manager and pass
        them as kwargs to psycopg2.connect (with sslmode=require for TLS)."""
        import json

        secret_payload = json.dumps({"username": "smc_app", "password": "hunter2"})
        fake_sm = MagicMock()
        fake_sm.get_secret_value.return_value = {"SecretString": secret_payload}
        fake_boto3_client = MagicMock(return_value=fake_sm)
        monkeypatch.setattr(bootstrap_mod, "_secretsmanager_client", fake_boto3_client)

        fake_connect = MagicMock(name="psycopg2.connect")
        monkeypatch.setattr(bootstrap_mod, "_psycopg2_connect", fake_connect)

        cfg = AppConfig(
            table_name="",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["*"],
            cognito_auth_enabled=False,
            use_rds=True,
            db_host="rds.example.com",
            db_name="smc",
            db_port=5432,
            db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:rds-cred-abcdef",
        )
        factory = bootstrap_mod._build_rds_connection_factory(cfg)
        # The factory is lazy: Secrets Manager is hit only when it's called.
        fake_sm.get_secret_value.assert_not_called()
        conn = factory()
        assert conn is fake_connect.return_value
        # Secret was fetched with the exact ARN.
        fake_sm.get_secret_value.assert_called_once()
        args, kwargs = fake_sm.get_secret_value.call_args
        assert kwargs.get("SecretId") == cfg.db_secret_arn or cfg.db_secret_arn in args
        # psycopg2.connect received sslmode=require (defense in depth).
        _, connect_kwargs = fake_connect.call_args
        assert connect_kwargs.get("sslmode") == "require"
        assert connect_kwargs.get("host") == "rds.example.com"
        assert connect_kwargs.get("port") == 5432
        assert connect_kwargs.get("dbname") == "smc"
        assert connect_kwargs.get("user") == "smc_app"
        assert connect_kwargs.get("password") == "hunter2"
