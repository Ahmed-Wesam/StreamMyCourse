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
        "DSQL_ENDPOINT",
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
        monkeypatch.setenv("DSQL_ENDPOINT", "  cluster.dsql.example  ")
        cfg = load_config()
        assert cfg.video_bucket == "my-bucket"
        assert cfg.dsql_endpoint == "cluster.dsql.example"


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


class TestDsqlEndpoint:
    """DSQL endpoint is the sole catalog database dependency."""

    def test_dsql_endpoint_empty_when_env_unset(self) -> None:
        cfg = load_config()
        assert cfg.dsql_endpoint == ""

    def test_dsql_endpoint_loaded_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DSQL_ENDPOINT", "abc.dsql.eu-west-1.on.aws")
        cfg = load_config()
        assert cfg.dsql_endpoint == "abc.dsql.eu-west-1.on.aws"

    def test_dsql_endpoint_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DSQL_ENDPOINT", "  cluster.dsql.example  ")
        cfg = load_config()
        assert cfg.dsql_endpoint == "cluster.dsql.example"


class TestMediaCleanupQueueUrl:
    def test_defaults_empty(self) -> None:
        cfg = load_config()
        assert cfg.media_cleanup_queue_url == ""

    def test_loaded_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MEDIA_CLEANUP_QUEUE_URL", "  https://sqs.example/q  ")
        cfg = load_config()
        assert cfg.media_cleanup_queue_url == "https://sqs.example/q"
