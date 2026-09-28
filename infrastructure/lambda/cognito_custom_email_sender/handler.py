"""Cognito CustomEmailSender — deliver codes via Zoho SMTP (existing domain mail)."""

from __future__ import annotations

import logging
from typing import Any, Dict

from decrypt import decrypt_verification_code
from mail import send_via_zoho_smtp
from smtp_config import load_zoho_smtp_config

logger = logging.getLogger(__name__)
_LOG_PREFIX = "cognito_custom_email_sender"


def _email_from_attributes(event: Dict[str, Any]) -> str:
    request = event.get("request") if isinstance(event.get("request"), dict) else {}
    attrs = request.get("userAttributes")
    if not isinstance(attrs, dict):
        return ""
    return str(attrs.get("email") or "").strip()


def _message_for_trigger(trigger_source: str, code: str) -> tuple[str, str]:
    if trigger_source == "CustomEmailSender_ForgotPassword":
        subject = "Reset your Research Spectrum password"
        body = (
            "Use this code to reset your password on Research Spectrum:\n\n"
            f"{code}\n\n"
            "Enter the code on the reset password page in the app. "
            "If you did not request this, you can ignore this email."
        )
        return subject, body
    if trigger_source in (
        "CustomEmailSender_SignUp",
        "CustomEmailSender_ResendCode",
        "CustomEmailSender_UpdateUserAttribute",
        "CustomEmailSender_VerifyUserAttribute",
    ):
        subject = "Verify your Research Spectrum account"
        body = (
            "Your verification code is:\n\n"
            f"{code}\n\n"
            "Enter this code on the verify email page in the app to finish creating your account."
        )
        return subject, body
    if trigger_source == "CustomEmailSender_AdminCreateUser":
        subject = "Your Research Spectrum account"
        body = (
            "Your temporary verification code is:\n\n"
            f"{code}\n\n"
            "Sign in at Research Spectrum and follow the prompts."
        )
        return subject, body
    subject = "Research Spectrum verification code"
    body = f"Your code is: {code}"
    return subject, body


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logging.getLogger().setLevel(logging.INFO)
    trigger = str(event.get("triggerSource") or "")
    if not trigger.startswith("CustomEmailSender_"):
        logger.warning("%s unexpected trigger %s; no-op", _LOG_PREFIX, trigger)
        return event

    to_address = _email_from_attributes(event)
    if not to_address:
        logger.error("%s missing recipient email", _LOG_PREFIX)
        raise ValueError("Missing recipient email")

    code = decrypt_verification_code(event)
    subject, body = _message_for_trigger(trigger, code)
    cfg = load_zoho_smtp_config()
    send_via_zoho_smtp(cfg=cfg, to_address=to_address, subject=subject, body_text=body)
    logger.info(
        "%s sent mail",
        _LOG_PREFIX,
        extra={"trigger": trigger, "to_domain": to_address.split("@")[-1] if "@" in to_address else ""},
    )
    return event
