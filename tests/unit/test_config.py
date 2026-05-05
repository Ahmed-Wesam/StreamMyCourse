from __future__ import annotations

import pytest

from config import AppConfig, load_config


# Every test should start from a clean env so OS-level vars don't leak in.
@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "VIDEO_BUCKET",
        "DEFAULT_MP4_URL",
        "VIDEO_URL",
        "ALLOWED_ORIGINS",
        "DB_HOST",
        "DB_NAME",
        "DB_PORT",
        "DB_SECRET_ARN",
        "COGNITO_AUTH_ENABLED",
        "LOG_LEVEL",
        "MEDIA_CLEANUP_QUEUE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


class TestLoadConfigDefaults:
    def test_defaults_when_env_unset(self) -> None:
        cfg = load_config()
        assert isinstance(cfg, AppConfig)
        assert cfg.video_bucket == ""
        assert cfg.video_url == ""
        assert cfg.default_mp4_url.endswith("flower.mp4")
        assert cfg.allowed_origins == []

    def test_app_config_is_frozen(self) -> None:
        cfg = load_config()
        with pytest.raises(Exception):
            cfg.video_bucket = "oops"  # type: ignore[misc]

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VIDEO_BUCKET", "  my-bucket  ")
        monkeypatch.setenv("DB_HOST", "  rds.example.com  ")
        cfg = load_config()
        assert cfg.video_bucket == "my-bucket"
        assert cfg.db_host == "rds.example.com"


class TestAllowedOrigins:
    def test_csv_split_with_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ALLOWED_ORIGINS", "a,b, c")
        cfg = load_config()
        assert cfg.allowed_origins == ["a", "b", "c"]

    def test_empty_string_defaults_to_empty_allowlist(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ALLOWED_ORIGINS", "")
        cfg = load_config()
        assert cfg.allowed_origins == []

    def test_whitespace_only_defaults_to_empty_allowlist(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ALLOWED_ORIGINS", "   ")
        cfg = load_config()
        assert cfg.allowed_origins == []

    def test_only_commas_yields_empty_allowlist(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ALLOWED_ORIGINS", ",,,")
        cfg = load_config()
        assert cfg.allowed_origins == []

    def test_explicit_star_yields_wildcard_sentinel(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ALLOWED_ORIGINS", "*")
        cfg = load_config()
        assert cfg.allowed_origins == ["*"]

    def test_single_origin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
        cfg = load_config()
        assert cfg.allowed_origins == ["https://app.example.com"]


class TestRdsFields:
    """RDS config fields are read from the environment for the PostgreSQL adapters."""

    def test_rds_fields_empty_when_env_unset(self) -> None:
        cfg = load_config()
        assert cfg.db_host == ""
        assert cfg.db_name == ""
        assert cfg.db_secret_arn == ""
        assert cfg.db_port == 5432

    def test_rds_fields_loaded_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_HOST", "rds.example.com")
        monkeypatch.setenv("DB_NAME", "streammycourse")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv(
            "DB_SECRET_ARN",
            "arn:aws:secretsmanager:eu-west-1:123:secret:rds-cred-abcdef",
        )
        cfg = load_config()
        assert cfg.db_host == "rds.example.com"
        assert cfg.db_name == "streammycourse"
        assert cfg.db_port == 5433
        assert cfg.db_secret_arn.startswith("arn:aws:secretsmanager:")

    def test_db_port_falls_back_to_default_on_non_integer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_PORT", "not-a-number")
        cfg = load_config()
        assert cfg.db_port == 5432

    def test_rds_fields_strip_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_HOST", "  rds.example.com  ")
        monkeypatch.setenv("DB_NAME", "  smc  ")
        monkeypatch.setenv("DB_SECRET_ARN", "  arn:aws:sm:eu:1:secret:x  ")
        cfg = load_config()
        assert cfg.db_host == "rds.example.com"
        assert cfg.db_name == "smc"
        assert cfg.db_secret_arn == "arn:aws:sm:eu:1:secret:x"


class TestMediaCleanupQueueUrl:
    def test_defaults_empty(self) -> None:
        cfg = load_config()
        assert cfg.media_cleanup_queue_url == ""

    def test_loaded_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MEDIA_CLEANUP_QUEUE_URL", "  https://sqs.example/q  ")
        cfg = load_config()
        assert cfg.media_cleanup_queue_url == "https://sqs.example/q"
