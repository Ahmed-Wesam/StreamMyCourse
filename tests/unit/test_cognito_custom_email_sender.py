"""Unit tests for Cognito custom email sender (Zoho SMTP)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LAMBDA_DIR = _REPO_ROOT / "infrastructure" / "lambda" / "cognito_custom_email_sender"


def _load_module(name: str, filename: str) -> ModuleType:
    lambda_dir = str(_LAMBDA_DIR)
    if lambda_dir not in sys.path:
        sys.path.insert(0, lambda_dir)
    path = _LAMBDA_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_decrypt_uses_encryption_sdk_with_pool_kms_key(monkeypatch: pytest.MonkeyPatch) -> None:
    decrypt = _load_module("ces_decrypt", "decrypt.py")
    monkeypatch.setenv("KMS_KEY_ARN", "arn:aws:kms:eu-west-1:111:key/abc")

    client = MagicMock()
    client.decrypt.return_value = (b"123456", object())

    event = {
        "userPoolId": "pool-1",
        "triggerSource": "CustomEmailSender_SignUp",
        "callerContext": {"clientId": "client-1"},
        "request": {"code": "YWFh", "userAttributes": {"email": "u@example.com"}},
    }
    code = decrypt.decrypt_verification_code(event, encryption_client=client, key_arn="arn:aws:kms:eu-west-1:111:key/abc")
    assert code == "123456"
    client.decrypt.assert_called_once()
    call_kwargs = client.decrypt.call_args.kwargs
    assert call_kwargs["source"] == b"aaa"


def test_handler_sends_forgot_password_via_smtp() -> None:
    handler = _load_module("ces_handler", "handler.py")
    smtp_config = _load_module("ces_smtp_config", "smtp_config.py")
    mail = _load_module("ces_mail", "mail.py")

    cfg = smtp_config.ZohoSmtpConfig(
        host="smtp.zoho.com",
        port=587,
        username="noreply@researchspectrum.org",
        password="secret",
        from_address="Research Spectrum <noreply@researchspectrum.org>",
        reply_to="support@researchspectrum.org",
    )
    sent: list[tuple[str, str, str]] = []

    def fake_send(*, cfg, to_address, subject, body_text, smtp_factory=None):  # type: ignore[no-untyped-def]
        sent.append((to_address, subject, body_text))

    event = {
        "triggerSource": "CustomEmailSender_ForgotPassword",
        "userPoolId": "pool-1",
        "callerContext": {"clientId": "c1"},
        "request": {
            "code": "YWFh",
            "userAttributes": {"email": "student@example.com"},
        },
    }

    with (
        patch.object(handler, "decrypt_verification_code", return_value="999888"),
        patch.object(handler, "load_zoho_smtp_config", return_value=cfg),
        patch.object(handler, "send_via_zoho_smtp", side_effect=fake_send),
    ):
        handler.lambda_handler(event, None)

    assert sent
    assert sent[0][0] == "student@example.com"
    assert "999888" in sent[0][2]
    assert "password" in sent[0][1].lower()


def test_smtp_config_requires_username_password() -> None:
    smtp_config = _load_module("ces_smtp_config2", "smtp_config.py")
    with pytest.raises(ValueError, match="smtp_username"):
        smtp_config._parse_secret(json.dumps({"smtp_username": "", "smtp_password": ""}))
