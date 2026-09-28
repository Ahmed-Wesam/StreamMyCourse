"""Contract tests for scripts/ensure-zoho-smtp-secret.sh (Zoho Cognito mail)."""

from __future__ import annotations

from pathlib import Path


def _script_text() -> str:
    path = Path(__file__).resolve().parents[2] / "scripts" / "ensure-zoho-smtp-secret.sh"
    return path.read_text(encoding="utf-8")


def test_script_fails_when_existing_secret_has_empty_password() -> None:
    text = _script_text()
    assert "smtp_password is empty" in text
    assert "ZOHO_SMTP_PASSWORD" in text


def test_script_emits_secret_arn_for_deploy() -> None:
    text = _script_text()
    assert "ZOHO_SMTP_SECRET_ARN=" in text
    assert "streammycourse/zoho-smtp/prod" in text


def test_script_uses_mailbox_login_and_noreply_from() -> None:
    text = _script_text()
    assert 'smtp_username: "support@researchspectrum.org"' in text
    assert "noreply@researchspectrum.org" in text
