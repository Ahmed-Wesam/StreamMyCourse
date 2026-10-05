"""Cognito auth helpers for integration tests (student single-session flows).

Never log full JWTs, refresh tokens, or passwords.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

import boto3
import pytest
from botocore.exceptions import BotoCoreError, ClientError

DEFAULT_AUTH_STACK = "StreamMyCourse-Auth-prod"
STUDENT_SESSION_CLAIM_KEYS = ("student_session_id", "custom:student_session_id")


@dataclass(frozen=True)
class StudentPoolConfig:
    user_pool_id: str
    client_id: str
    region: str


@dataclass(frozen=True)
class StudentCognitoConfig:
    user_pool_id: str
    client_id: str
    region: str
    username: str
    password: str


@dataclass(frozen=True)
class StudentAuthTokens:
    id_token: str
    access_token: str
    refresh_token: str
    student_session_id: str | None


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload (no signature verify)."""
    parts = (token or "").strip().split(".")
    if len(parts) < 2:
        raise ValueError("JWT must have at least header and payload segments")
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
    return json.loads(payload_bytes.decode("utf-8"))


def student_session_id_from_id_token(id_token: str) -> str | None:
    """Return ``student_session_id`` claim from a student IdToken, if present."""
    payload = decode_jwt_payload(id_token)
    for key in STUDENT_SESSION_CLAIM_KEYS:
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _integration_region() -> str:
    return os.environ.get("INTEGRATION_AWS_REGION", "eu-west-1").strip() or "eu-west-1"


def _auth_stack_name() -> str:
    return os.environ.get("INTEGRATION_AUTH_STACK", DEFAULT_AUTH_STACK).strip() or DEFAULT_AUTH_STACK


def _student_username() -> str:
    for key in (
        "LOCAL_COGNITO_USERNAME_STUDENT",
        "COGNITO_TEST_USERNAME_STUDENT",
        "INTEGRATION_COGNITO_USERNAME_STUDENT",
    ):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return "ci-student@noreply.local"


def _student_password() -> str | None:
    for key in (
        "LOCAL_COGNITO_PASSWORD_STUDENT",
        "COGNITO_TEST_PASSWORD_STUDENT",
        "INTEGRATION_COGNITO_PASSWORD_STUDENT",
    ):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def _cfn_output(*, stack_name: str, output_key: str, region: str) -> str | None:
    cf = boto3.client("cloudformation", region_name=region)
    resp = cf.describe_stacks(StackName=stack_name)
    stacks = resp.get("Stacks") or []
    if not stacks:
        return None
    for item in stacks[0].get("Outputs") or []:
        if item.get("OutputKey") == output_key:
            value = str(item.get("OutputValue") or "").strip()
            return value or None
    return None


def resolve_student_pool_config_or_skip() -> StudentPoolConfig:
    """Resolve student user pool + app client from CloudFormation (no CI password required)."""
    region = _integration_region()
    stack = _auth_stack_name()
    try:
        user_pool_id = _cfn_output(stack_name=stack, output_key="UserPoolId", region=region)
        client_id = _cfn_output(
            stack_name=stack, output_key="StudentUserPoolClientId", region=region
        )
    except (BotoCoreError, ClientError) as exc:
        pytest.skip(f"Could not resolve auth stack outputs ({stack}): {exc}")

    if not user_pool_id or not client_id:
        pytest.skip(
            f"Auth stack {stack} missing UserPoolId or StudentUserPoolClientId outputs"
        )

    return StudentPoolConfig(
        user_pool_id=user_pool_id,
        client_id=client_id,
        region=region,
    )


def student_client_supports_native_signup(cfg: StudentPoolConfig) -> bool:
    """True when the student app client allows RS-6 native sign-up + admin password auth."""
    cognito = boto3.client("cognito-idp", region_name=cfg.region)
    try:
        resp = cognito.describe_user_pool_client(
            UserPoolId=cfg.user_pool_id,
            ClientId=cfg.client_id,
        )
    except (BotoCoreError, ClientError) as exc:
        pytest.skip(f"describe_user_pool_client failed: {exc}")

    client = resp.get("UserPoolClient") or {}
    flows = client.get("ExplicitAuthFlows") or []
    providers = client.get("SupportedIdentityProviders") or []
    return (
        "ALLOW_USER_SRP_AUTH" in flows
        and "ALLOW_ADMIN_USER_PASSWORD_AUTH" in flows
        and "COGNITO" in providers
    )


def admin_delete_cognito_user(*, cfg: StudentPoolConfig, username: str) -> None:
    """Best-effort delete of a disposable integration user."""
    cognito = boto3.client("cognito-idp", region_name=cfg.region)
    try:
        cognito.admin_delete_user(UserPoolId=cfg.user_pool_id, Username=username)
    except (BotoCoreError, ClientError):
        return


def mint_native_signup_tokens(
    *,
    cfg: StudentPoolConfig,
    email: str,
    password: str,
) -> StudentAuthTokens:
    """Public sign_up, admin confirm (bypass email), then AdminInitiateAuth for tokens."""
    cognito = boto3.client("cognito-idp", region_name=cfg.region)
    try:
        cognito.sign_up(
            ClientId=cfg.client_id,
            Username=email,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", "") or "")
        if code in ("NotAuthorizedException", "InvalidParameterException"):
            pytest.skip(f"Student client does not allow public sign_up ({code})")
        pytest.fail(f"Cognito sign_up failed ({code}): {exc}")
    except BotoCoreError as exc:
        pytest.fail(f"Cognito sign_up failed: {exc}")

    try:
        cognito.admin_confirm_sign_up(UserPoolId=cfg.user_pool_id, Username=email)
        cognito.admin_set_user_password(
            UserPoolId=cfg.user_pool_id,
            Username=email,
            Password=password,
            Permanent=True,
        )
        resp = cognito.admin_initiate_auth(
            UserPoolId=cfg.user_pool_id,
            ClientId=cfg.client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except (BotoCoreError, ClientError) as exc:
        pytest.fail(f"Native signup confirm/auth failed: {exc}")

    auth = resp.get("AuthenticationResult") or {}
    id_token = str(auth.get("IdToken") or "").strip()
    access_token = str(auth.get("AccessToken") or "").strip()
    refresh_token = str(auth.get("RefreshToken") or "").strip()
    if not id_token:
        pytest.fail("admin_initiate_auth after sign_up did not return IdToken")

    return StudentAuthTokens(
        id_token=id_token,
        access_token=access_token,
        refresh_token=refresh_token,
        student_session_id=student_session_id_from_id_token(id_token),
    )


def resolve_student_cognito_config_or_skip() -> StudentCognitoConfig:
    """Resolve student pool/client from CloudFormation; skip when prerequisites missing."""
    password = _student_password()
    if not password:
        pytest.skip(
            "Student Cognito password not set "
            "(LOCAL_COGNITO_PASSWORD_STUDENT / COGNITO_TEST_PASSWORD_STUDENT / "
            "INTEGRATION_COGNITO_PASSWORD_STUDENT)"
        )

    pool = resolve_student_pool_config_or_skip()
    return StudentCognitoConfig(
        user_pool_id=pool.user_pool_id,
        client_id=pool.client_id,
        region=pool.region,
        username=_student_username(),
        password=password,
    )


def mint_student_password_auth(cfg: StudentCognitoConfig) -> StudentAuthTokens:
    """Mint Id/access/refresh tokens via AdminInitiateAuth (student app client)."""
    cognito = boto3.client("cognito-idp", region_name=cfg.region)
    try:
        resp = cognito.admin_initiate_auth(
            UserPoolId=cfg.user_pool_id,
            ClientId=cfg.client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": cfg.username,
                "PASSWORD": cfg.password,
            },
        )
    except (BotoCoreError, ClientError) as exc:
        pytest.fail(f"admin_initiate_auth failed for student user: {exc}")

    auth = resp.get("AuthenticationResult") or {}
    id_token = str(auth.get("IdToken") or "").strip()
    access_token = str(auth.get("AccessToken") or "").strip()
    refresh_token = str(auth.get("RefreshToken") or "").strip()
    if not id_token or not refresh_token:
        pytest.fail("admin_initiate_auth did not return IdToken and RefreshToken")

    return StudentAuthTokens(
        id_token=id_token,
        access_token=access_token,
        refresh_token=refresh_token,
        student_session_id=student_session_id_from_id_token(id_token),
    )


def try_refresh_student_tokens_with_metadata(
    *,
    cfg: StudentCognitoConfig,
    refresh_token: str,
    student_session_id: str,
) -> dict[str, str] | None:
    """Attempt GetTokensFromRefreshToken with ClientMetadata; None when refresh is denied."""
    cognito = boto3.client("cognito-idp", region_name=cfg.region)
    try:
        if hasattr(cognito, "get_tokens_from_refresh_token"):
            resp = cognito.get_tokens_from_refresh_token(
                RefreshToken=refresh_token,
                ClientId=cfg.client_id,
                ClientMetadata={"student_session_id": student_session_id},
            )
        else:
            resp = cognito.initiate_auth(
                ClientId=cfg.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": refresh_token},
            )
    except (BotoCoreError, ClientError, AttributeError):
        return None

    id_token = str(resp.get("IdToken") or "").strip()
    if not id_token:
        auth = resp.get("AuthenticationResult") or {}
        id_token = str(auth.get("IdToken") or "").strip()
    if not id_token:
        return None
    return {"IdToken": id_token}
