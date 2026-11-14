"""Catalog unconfigured message mentions DSQL dependency."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import index as index_mod
from config import AppConfig


def _bootstrap_unconfigured(cfg: AppConfig):
    return (cfg, None, None, None, None, None, None, None)


@pytest.fixture
def cfg_wildcard() -> AppConfig:
    return AppConfig(
        video_bucket="",
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
    )


def test_catalog_unconfigured_message_lists_dsql_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    cfg_wildcard: AppConfig,
    make_lambda_event,
) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    monkeypatch.setattr(
        index_mod,
        "lambda_bootstrap",
        lambda: _bootstrap_unconfigured(cfg_wildcard),
    )
    evt = make_lambda_event(method="GET", path="/courses")
    resp = index_mod.lambda_handler(evt, None)
    body = json.loads(resp["body"])
    assert body["code"] == "catalog_unconfigured"
    msg = body["message"]
    assert "DSQL_ENDPOINT" in msg
    assert "DB_HOST" not in msg
