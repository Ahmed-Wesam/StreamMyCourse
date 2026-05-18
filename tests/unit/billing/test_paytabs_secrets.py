"""Tests for PayTabs Secrets Manager loader."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict

import pytest

from paytabs_secrets import PaytabsCredentials, clear_paytabs_secret_cache, load_paytabs_from_secret


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_paytabs_secret_cache()
    yield
    clear_paytabs_secret_cache()


def test_load_paytabs_from_secret_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "server_key": "key-1",
        "profile_id": "profile-1",
        "api_domain": "secure-jordan.paytabs.com",
    }

    class _FakeClient:
        def get_secret_value(self, *, SecretId: str) -> Dict[str, Any]:
            assert SecretId == "streammycourse/paytabs/dev"
            return {"SecretString": json.dumps(payload)}

    class _FakeBoto3:
        @staticmethod
        def client(service_name: str) -> _FakeClient:
            assert service_name == "secretsmanager"
            return _FakeClient()

    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3())

    creds = load_paytabs_from_secret("streammycourse/paytabs/dev")
    assert creds == PaytabsCredentials(
        server_key="key-1",
        profile_id="profile-1",
        api_domain="secure-jordan.paytabs.com",
    )


def test_load_paytabs_from_secret_returns_none_for_empty_id() -> None:
    assert load_paytabs_from_secret("") is None
    assert load_paytabs_from_secret("   ") is None
