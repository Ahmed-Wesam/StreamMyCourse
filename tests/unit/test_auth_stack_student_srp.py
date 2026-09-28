"""Contract tests: auth-stack.yaml student native auth + PreSignUp/Zoho CustomEmailSender wiring."""

from __future__ import annotations

import re
from pathlib import Path


def _auth_stack_text() -> str:
    path = Path(__file__).resolve().parents[2] / "infrastructure" / "templates" / "auth-stack.yaml"
    return path.read_text(encoding="utf-8")


def test_student_client_enables_srp_and_cognito_idp() -> None:
    text = _auth_stack_text()
    student_block = text[text.index("StudentUserPoolClient:") : text.index("TeacherUserPoolClient:")]
    assert "ALLOW_USER_SRP_AUTH" in student_block
    assert "ALLOW_REFRESH_TOKEN_AUTH" in student_block
    assert "ALLOW_ADMIN_USER_PASSWORD_AUTH" in student_block
    assert "ALLOW_USER_PASSWORD_AUTH" not in student_block
    assert re.search(r"SupportedIdentityProviders:\s*\n\s+- COGNITO\s*\n\s+- Google", student_block)


def test_teacher_client_remains_google_only_oauth() -> None:
    text = _auth_stack_text()
    teacher_block = text[text.index("TeacherUserPoolClient:") : text.index("CatalogUserPoolDomain:")]
    assert "ALLOW_USER_SRP_AUTH" not in teacher_block
    assert re.search(r"SupportedIdentityProviders:\s*\n\s+- Google\s*$", teacher_block, re.M)


def test_pre_signup_lambda_and_permissions_wired() -> None:
    text = _auth_stack_text()
    assert "CognitoPreSignUpLambda:" in text
    assert "Handler: handler.lambda_handler" in text
    assert "VpcConfig" not in text[
        text.index("CognitoPreSignUpLambda:") : text.index("CognitoCustomEmailSenderLambda:")
    ]
    assert "Condition: ShouldDeployPreSignUp" in text
    assert "CognitoPreSignUpLambdaPermission:" in text
    assert "cognito-idp:ListUsers" in text
    assert "cognito-idp:AdminLinkProviderForUser" in text
    assert "CognitoPreSignUpLambdaPoolPolicy:" in text


def test_lambda_config_merges_pre_signup_with_profile_sync() -> None:
    text = _auth_stack_text()
    assert "ShouldDeployUserProfileSyncAndPreSignUp" in text
    assert "PreSignUp: !GetAtt CognitoPreSignUpLambda.Arn" in text
    assert "PostAuthentication: !GetAtt UserProfileSyncLambda.Arn" in text


def test_zoho_custom_email_sender_when_pre_signup_and_secret_deploy() -> None:
    text = _auth_stack_text()
    assert "ShouldDeployCustomEmailSender" in text
    assert "CognitoCustomEmailSenderLambda:" in text
    assert "CognitoCustomEmailKmsKey:" in text
    assert "CustomEmailSender:" in text
    assert "LambdaVersion: V1_0" in text
    assert "KMSKeyID:" in text
    assert "CognitoCustomEmailSenderLambdaPermission:" in text
    assert "ZohoSmtpSecretArn" in text
    assert "EmailSendingAccount: COGNITO_DEFAULT" in text
    assert "EmailSendingAccount: DEVELOPER" not in text
    assert "AWS::SES::EmailIdentity" not in text
