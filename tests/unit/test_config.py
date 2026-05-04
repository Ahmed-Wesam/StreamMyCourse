from __future__ import annotations

import pytest

from config import AppConfig, load_config


# Every test should start from a clean env so OS-level vars don't leak in.
@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "TABLE_NAME",
        "VIDEO_BUCKET",
        "DEFAULT_MP4_URL",
        "VIDEO_URL",
        "ALLOWED_ORIGINS",
        "USE_RDS",
        "DB_HOST",
        "DB_NAME",
        "DB_PORT",
        "DB_SECRET_ARN",
    ):
        monkeypatch.delenv(name, raising=False)


class TestLoadConfigDefaults:
    def test_defaults_when_env_unset(self) -> None:
        cfg = load_config()
        assert isinstance(cfg, AppConfig)
        assert cfg.table_name == ""
        assert cfg.video_bucket == ""
        assert cfg.video_url == ""
        # Default Mozilla MDN sample video — pin so a refactor doesn't quietly
        # change the fallback.
        assert cfg.default_mp4_url.endswith("flower.mp4")
        # Fail-secure: no implicit wildcard when ALLOWED_ORIGINS is unset.
        assert cfg.allowed_origins == []

    def test_app_config_is_frozen(self) -> None:
        cfg = load_config()
        with pytest.raises(Exception):
            cfg.table_name = "oops"  # type: ignore[misc]

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TABLE_NAME", "  my-table  ")
        monkeypatch.setenv("VIDEO_BUCKET", "  my-bucket  ")
        cfg = load_config()
        assert cfg.table_name == "my-table"
        assert cfg.video_bucket == "my-bucket"


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
        # `_split_csv` drops empty parts, so a CSV of pure separators yields `[]`.
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
    """RDS config fields back the PostgreSQL adapter path. With USE_RDS unset or
    falsy the catalog keeps talking to DynamoDB (rollback path) so defaults must
    be safe/no-ops."""

    def test_use_rds_defaults_false_when_env_unset(self) -> None:
        cfg = load_config()
        assert cfg.use_rds is False

    def test_use_rds_true_when_env_set_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("USE_RDS", "true")
        cfg = load_config()
        assert cfg.use_rds is True

    def test_use_rds_case_insensitive_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("USE_RDS", "TRUE")
        cfg = load_config()
        assert cfg.use_rds is True

    def test_use_rds_false_for_any_other_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for value in ("", "false", "0", "no", "nope"):
            monkeypatch.setenv("USE_RDS", value)
            cfg = load_config()
            assert cfg.use_rds is False, f"USE_RDS={value!r} should resolve to False"

    def test_rds_fields_empty_when_env_unset(self) -> None:
        cfg = load_config()
        assert cfg.db_host == ""
        assert cfg.db_name == ""
        assert cfg.db_secret_arn == ""
        # PostgreSQL default port is 5432 -- loader fills this in so the adapter
        # does not need to repeat the default in every code path.
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
        # A malformed DB_PORT (e.g. unresolved CloudFormation import) must not
        # crash load_config at cold start -- fall back to 5432 and let the
        # connection attempt fail loudly downstream instead.
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
