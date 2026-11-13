"""DSQL-2 S6: operator delete-user against preview DSQL + Cognito."""

from __future__ import annotations

import importlib.util
import os
import secrets
import string
import sys
import uuid
from pathlib import Path
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.cognito_auth import (
    admin_delete_cognito_user,
    mint_native_signup_tokens,
    resolve_student_pool_config_or_skip,
)
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.dsql_preview_access import delete_purchase_by_id, insert_paid_bundle_purchase
from helpers.factories import build_course_factory, build_lesson_factory

_REPO = Path(__file__).resolve().parents[2]


def _is_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip().endswith("Api-dsql")


pytestmark = pytest.mark.skipif(
    not _is_preview_stack(),
    reason="user deletion integration runs only on StreamMyCourse-Api-dsql",
)


def _email() -> str:
    return f"del-test-{uuid.uuid4().hex[:12]}@researchspectrum.org"


def _password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return f"Rs6!{''.join(secrets.choice(alphabet) for _ in range(20))}aA1"


def _load_delete_user():
    path = _REPO / "scripts" / "delete-user.py"
    spec = importlib.util.spec_from_file_location("delete_user_int", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    catalog = _REPO / "infrastructure" / "lambda" / "catalog"
    if str(catalog) not in sys.path:
        sys.path.insert(0, str(catalog))
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


@pytest.fixture
def teacher_api(api_base_url: str) -> Iterator[ApiClient]:
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT not set")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=api_base_url, timeout=30.0, headers=headers) as client:
        yield ApiClient(client)


def _sql_user_learning_counts(conn, user_sub: str) -> tuple[int, int, int, int]:
    users = int(execute_scalar(conn, "SELECT COUNT(*) FROM users WHERE user_sub = %s", (user_sub,)) or 0)
    progress = int(
        execute_scalar(conn, "SELECT COUNT(*) FROM lesson_progress WHERE user_sub = %s", (user_sub,)) or 0
    )
    notes = int(
        execute_scalar(conn, "SELECT COUNT(*) FROM lesson_notes WHERE user_sub = %s", (user_sub,)) or 0
    )
    days = int(
        execute_scalar(
            conn, "SELECT COUNT(*) FROM learning_activity_days WHERE user_sub = %s", (user_sub,)
        )
        or 0
    )
    return users, progress, notes, days


def test_operator_delete_user_removes_dsql_row_and_cognito(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    email = _email()
    password = _password()
    mod = _load_delete_user()
    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    headers = {"Authorization": f"Bearer {tokens.id_token}"}
    me = api.get_users_me(headers=headers)
    assert me.status_code == 200, me.text
    body = me.json()
    user_sub = str(body.get("userId") or body.get("cognitoSub") or "")
    assert user_sub

    rc = mod.run(
        ["--user-sub", user_sub, "--execute"],
        cognito=mod._BotoCognito(),
        service_factory=mod._build_service,
        endpoint_resolver=mod._resolve_dsql_endpoint,
        pool_resolver=mod._resolve_user_pool_id,
    )
    assert rc == 0, "delete-user.py should exit 0"

    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE user_sub = %s", (user_sub,))
            row = cur.fetchone()
            assert row is not None and int(row[0]) == 0

    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("cognito-idp")
    with pytest.raises(ClientError) as exc:
        client.admin_get_user(UserPoolId=pool.user_pool_id, Username=email)
    assert exc.value.response["Error"]["Code"] == "UserNotFoundException"


def test_operator_delete_user_clears_progress_notes_and_activity_days(
    api_base_url: str,
    teacher_api: ApiClient,
) -> None:
    """Throwaway native user with bundle, progress, and note — operator delete clears DSQL rows."""
    pool = resolve_student_pool_config_or_skip()
    email = _email()
    password = _password()
    email_for_cleanup = email
    purchase_id = ""
    course_ids: list[str] = []
    course_factory = build_course_factory(teacher_api, course_ids.append)
    lesson_factory = build_lesson_factory(teacher_api)

    try:
        tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
        headers = {"Authorization": f"Bearer {tokens.id_token}"}
        with httpx.Client(
            base_url=api_base_url, timeout=30.0, headers=headers
        ) as disposable_client:
            disposable = ApiClient(disposable_client)

            me = disposable.get_users_me()
            assert me.status_code == 200, me.text
            user_sub = str(me.json().get("userId") or me.json().get("cognitoSub") or "")
            assert user_sub

            course = course_factory(label="user-del-lr")
            lesson = lesson_factory(course.course_id, label="user-del-lesson")
            assert (
                teacher_api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id).status_code
                == 200
            )
            assert teacher_api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
            assert teacher_api.publish_course(course.course_id).status_code == 200

            purchase_id = insert_paid_bundle_purchase(user_sub)

            complete = disposable.update_lesson_progress(
                course.course_id,
                lesson.lesson_id,
                position=100,
                duration=100,
                mark_complete=True,
            )
            assert complete.status_code == 200, complete.text
            note = disposable.create_lesson_note(
                course.course_id, lesson.lesson_id, body="user-del-note"
            )
            assert note.status_code == 201, note.text

            delete_purchase_by_id(purchase_id)
            purchase_id = ""

            mod = _load_delete_user()
            rc = mod.run(
                ["--user-sub", user_sub, "--execute"],
                cognito=mod._BotoCognito(),
                service_factory=mod._build_service,
                endpoint_resolver=mod._resolve_dsql_endpoint,
                pool_resolver=mod._resolve_user_pool_id,
            )
            assert rc == 0, "delete-user.py should exit 0"
            email_for_cleanup = ""

            with admin_connect() as conn:
                counts = _sql_user_learning_counts(conn, user_sub)
            assert counts == (0, 0, 0, 0)
    finally:
        if purchase_id:
            delete_purchase_by_id(purchase_id)
        for course_id in course_ids:
            try:
                teacher_api.delete_course(course_id)
            except Exception:
                pass
        if email_for_cleanup:
            admin_delete_cognito_user(cfg=pool, username=email_for_cleanup)
