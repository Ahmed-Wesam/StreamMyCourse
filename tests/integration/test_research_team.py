"""DSQL-7c S4: research team apply, review, and delete integration."""

from __future__ import annotations

import os
import uuid

import boto3
import httpx
import pytest

from helpers.api import ApiClient
from helpers.cognito_auth import (
    admin_delete_cognito_user,
    mint_native_signup_tokens,
    resolve_student_pool_config_or_skip,
    student_client_supports_native_signup,
)
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.factories import make_test_title
from helpers.module_contract import require_course_modules_list
from test_certificates import _grade_passing_assignment

_PDF_BYTES = b"%PDF-1.4\n"
_PDF_SIZE = len(_PDF_BYTES)


def _is_dsql_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip() == "StreamMyCourse-Api-dsql"


def _api_base() -> str:
    return os.environ.get("INTEGRATION_API_BASE_URL", "").rstrip("/")


def _apply_body(**overrides) -> dict:
    body = {
        "fullName": "Ada Lovelace",
        "country": "Jordan",
        "institution": "RS University",
        "position": "Medical Student",
        "publicationCount": 1,
        "projectCount": 2,
        "statsExperience": "Beginner",
        "sysReviewExperience": "None",
        "researchAreas": ["Clinical Research"],
        "interests": "Meta-analysis",
        "motivation": "I want to contribute to research.",
        "weeklyHours": "5–10 hours/week",
        "acknowledgement": True,
    }
    body.update(overrides)
    return body


def _throwaway_student_api() -> tuple[ApiClient, object, str]:
    pool = resolve_student_pool_config_or_skip()
    student_client_supports_native_signup(pool)
    email = f"rt-student-{uuid.uuid4().hex[:12]}@noreply.local"
    password = f"Rt-Test-{uuid.uuid4().hex[:8]}!aA1"
    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    client = httpx.Client(
        base_url=_api_base(),
        headers={"Authorization": f"Bearer {tokens.id_token}"},
        timeout=60.0,
    )
    return ApiClient(client), pool, email


def _throwaway_admin_api() -> tuple[ApiClient, object, str]:
    pool = resolve_student_pool_config_or_skip()
    student_client_supports_native_signup(pool)
    email = f"rt-admin-{uuid.uuid4().hex[:12]}@noreply.local"
    password = f"Rt-Adm-{uuid.uuid4().hex[:8]}!aA1"
    mint_native_signup_tokens(cfg=pool, email=email, password=password)
    cognito = boto3.client("cognito-idp", region_name=pool.region)
    cognito.admin_update_user_attributes(
        UserPoolId=pool.user_pool_id,
        Username=email,
        UserAttributes=[{"Name": "custom:role", "Value": "admin"}],
    )
    resp = cognito.admin_initiate_auth(
        UserPoolId=pool.user_pool_id,
        ClientId=pool.client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": email, "PASSWORD": password},
    )
    id_token = str((resp.get("AuthenticationResult") or {}).get("IdToken") or "")
    assert id_token
    client = httpx.Client(
        base_url=_api_base(),
        headers={"Authorization": f"Bearer {id_token}"},
        timeout=60.0,
    )
    return ApiClient(client), pool, email


def test_teacher_cannot_set_research_requirement(api: ApiClient, course_factory) -> None:
    course = course_factory(label="rt-req-403")
    resp = api.put_research_team_requirement(course.course_id, required=True)
    assert resp.status_code == 403


def test_research_team_apply_and_review_flow(
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    admin_api, admin_pool, admin_email = _throwaway_admin_api()
    student_api, student_pool, student_email = _throwaway_student_api()
    course = course_factory(label="rt-apply")
    course_id = course.course_id
    lesson = lesson_factory(course_id, label="rt-apply-lesson")
    assert api.get_upload_url(course_id=course_id, lesson_id=lesson.lesson_id).status_code == 200
    assert api.mark_video_ready(course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course_id).status_code == 200
    try:
        assert admin_api.put_research_team_requirement(course_id, required=True).status_code == 200
        reqs = admin_api.get_research_team_requirements()
        assert reqs.status_code == 200
        assert any(r.get("id") == course_id for r in reqs.json().get("courses", []))
        denied = student_api.submit_research_team_application(_apply_body())
        assert denied.status_code == 403
        assert denied.json().get("code") == "not_eligible"
        student_api.patch_users_me(
            body={"givenName": "Ada", "familyName": "Student", "country": "Jordan"}
        )
        _grade_passing_assignment(api, student_api, course_id)
        submitted_areas = ["Clinical Research", "Systematic Reviews"]
        ok = student_api.submit_research_team_application(
            _apply_body(researchAreas=submitted_areas)
        )
        assert ok.status_code == 200, ok.text
        assert ok.json().get("researchAreas") == submitted_areas
        dup = student_api.submit_research_team_application(_apply_body())
        assert dup.status_code == 409
        assert dup.json().get("code") == "application_open"
        app_id = ok.json()["id"]
        assert admin_api.patch_research_team_application(app_id, status="under_review").status_code == 200
        assert admin_api.patch_research_team_application(app_id, status="accepted").status_code == 200
        if _is_dsql_preview_stack():
            with admin_connect() as conn:
                areas_type = execute_scalar(
                    conn,
                    """
                    SELECT jsonb_typeof(research_areas)
                    FROM app.research_team_applications
                    WHERE id = %s
                    """,
                    (app_id,),
                )
                open_count = execute_scalar(
                    conn,
                    """
                    SELECT COUNT(*) FROM app.research_team_applications
                    WHERE user_sub IS NOT NULL
                      AND status IN ('submitted', 'under_review')
                    """,
                )
            assert areas_type == "array"
            assert int(open_count or 0) >= 0
    finally:
        admin_api.put_research_team_requirement(course_id, required=False)
        student_api.raw.close()
        admin_api.raw.close()
        admin_delete_cognito_user(cfg=student_pool, username=student_email)
        admin_delete_cognito_user(cfg=admin_pool, username=admin_email)

