"""Tests for HyperPay Secrets Manager loader."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict

import pytest

from hyperpay_secrets import (
    HyperpayCredentials,
    clear_hyperpay_secret_cache,
    load_hyperpay_from_secret,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_hyperpay_secret_cache()
    yield
    clear_hyperpay_secret_cache()


def test_load_hyperpay_from_secret_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "access_token": "tok-abc",
        "entity_id": "entity-1",
        "webhook_secret": "a" * 64,
        "api_host": "eu-test.oppwa.com",
    }

    class _FakeClient:
        def get_secret_value(self, *, SecretId: str) -> Dict[str, Any]:
            assert SecretId == "streammycourse/hyperpay/dev"
            return {"SecretString": json.dumps(payload)}

    class _FakeBoto3:
        @staticmethod
        def client(service_name: str) -> _FakeClient:
            assert service_name == "secretsmanager"
            return _FakeClient()

    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3())

    creds = load_hyperpay_from_secret("streammycourse/hyperpay/dev")
    assert creds == HyperpayCredentials(
        access_token="tok-abc",
        entity_id="entity-1",
        webhook_secret="a" * 64,
        api_host="eu-test.oppwa.com",
    )


def test_load_hyperpay_from_secret_returns_none_for_empty_id() -> None:
    assert load_hyperpay_from_secret("") is None
    assert load_hyperpay_from_secret("   ") is None


def test_load_hyperpay_from_secret_returns_none_when_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"entity_id": "entity-1"}

    class _FakeClient:
        def get_secret_value(self, *, SecretId: str) -> Dict[str, Any]:
            return {"SecretString": json.dumps(payload)}

    class _FakeBoto3:
        @staticmethod
        def client(service_name: str) -> _FakeClient:
            return _FakeClient()

    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3())
    assert load_hyperpay_from_secret("streammycourse/hyperpay/dev") is None


def test_load_hyperpay_from_secret_returns_none_when_entity_id_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"access_token": "tok-abc"}

    class _FakeClient:
        def get_secret_value(self, *, SecretId: str) -> Dict[str, Any]:
            return {"SecretString": json.dumps(payload)}

    class _FakeBoto3:
        @staticmethod
        def client(service_name: str) -> _FakeClient:
            return _FakeClient()

    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3())
    assert load_hyperpay_from_secret("streammycourse/hyperpay/dev") is None
