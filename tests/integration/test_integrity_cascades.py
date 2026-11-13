"""DSQL-8 S4: prod-capable delete-registry and fulfillment integrity."""

from __future__ import annotations

import importlib.util
import os
import secrets
import string
import sys
import uuid
from pathlib import Path
import boto3
import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import billing_environment, decode_jwt_sub
from helpers.cognito_auth import (
    admin_delete_cognito_user,
    mint_native_signup_tokens,
    resolve_student_pool_config_or_skip,
)
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.dsql_billing_integration import delete_webhook_events
from helpers.dsql_preview_access import delete_purchase_by_id, insert_paid_bundle_purchase
from helpers.factories import build_course_factory, build_lesson_factory

_REPO = Path(__file__).resolve().parents[2]
_FULFILL_SRC = _REPO / "infrastructure" / "lambda" / "billing_fulfillment"
_CATALOG = _REPO / "infrastructure" / "lambda" / "catalog"
_DB_TX_PATH = _CATALOG / "services" / "common" / "db_tx.py"


def _ensure_fulfillment_importable() -> None:
    if "db_tx" not in sys.modules:
        spec = importlib.util.spec_from_file_location("db_tx", _DB_TX_PATH)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["db_tx"] = mod
    if str(_CATALOG) not in sys.path:
        sys.path.insert(0, str(_CATALOG))
    if str(_FULFILL_SRC) not in sys.path:
        sys.path.insert(0, str(_FULFILL_SRC))


def _runs_on_target_stack() -> bool:
    stack = os.environ.get("INTEGRATION_API_STACK", "StreamMyCourse-Api-prod").strip()
    if stack.endswith("Api-dsql"):
        return True
    if not stack.endswith("Api-prod"):
        return False
    region = os.environ.get("INTEGRATION_AWS_REGION", "eu-west-1")
    try:
        cfg = boto3.client("lambda", region_name=region).get_function_configuration(
            FunctionName="StreamMyCourse-Catalog-prod"
        )
    except Exception:
        return False
    env = (cfg.get("Environment") or {}).get("Variables") or {}
    return bool((env.get("DSQL_ENDPOINT") or "").strip()) and not (env.get("DB_HOST") or "").strip()


pytestmark = pytest.mark.skipif(
    not _runs_on_target_stack(),
    reason="integrity cascades: Api-dsql or prod catalog on DSQL",
)


def _email() -> str:
    return f"integ-{uuid.uuid4().hex[:12]}@researchspectrum.org"


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


def test_delete_student_leaves_course_then_course_delete_removes_rows(
    api_base_url: str,
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    pool = resolve_student_pool_config_or_skip()
    email, password = _email(), _password()
    course = course_factory(label="integ-del-student")
    lesson = lesson_factory(course.course_id, label="integ-lesson")
    assert api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id).status_code == 200
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200

    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    headers = {"Authorization": f"Bearer {tokens.id_token}"}
    import httpx

    with httpx.Client(base_url=api_base_url, timeout=30.0, headers=headers) as client:
        student = ApiClient(client)
        me = student.get_users_me()
        assert me.status_code == 200, me.text
        student_sub = str(me.json().get("userId") or me.json().get("cognitoSub") or "")
        assert student_sub
        insert_paid_bundle_purchase(student_sub)
        assert (
            student.update_lesson_progress(
                course.course_id, lesson.lesson_id, position=90, duration=100, mark_complete=True
            ).status_code
            == 200
        )
        assert student.create_lesson_note(course.course_id, lesson.lesson_id, body="cascade note").status_code == 201

    delete_user = _load_delete_user()
    rc = delete_user.run(
        ["--user-sub", student_sub, "--execute"],
        cognito=delete_user._BotoCognito(),
        service_factory=delete_user._build_service,
        endpoint_resolver=delete_user._resolve_dsql_endpoint,
        pool_resolver=delete_user._resolve_user_pool_id,
    )
    assert rc == 0

    assert api.get_course(course.course_id).status_code == 200
    with admin_connect() as conn:
        assert execute_scalar(conn, "SELECT COUNT(*) FROM app.users WHERE user_sub = %s", (student_sub,)) == 0
        assert (
            execute_scalar(
                conn,
                "SELECT COUNT(*) FROM app.lesson_notes WHERE user_sub = %s",
                (student_sub,),
            )
            == 0
        )

    assert api.delete_course(course.course_id).status_code == 200
    with admin_connect() as conn:
        assert execute_scalar(conn, "SELECT COUNT(*) FROM app.courses WHERE id = %s", (course.course_id,)) == 0


def test_course_delete_with_purchase_is_409(api: ApiClient, course_factory) -> None:
    course = course_factory(label="integ-purchase-409")
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    assert token
    user_sub = decode_jwt_sub(token)
    purchase_id = str(uuid.uuid4())
    env = billing_environment()
    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.purchases (
                    id, user_sub, environment, product_type, course_id,
                    status, amount_minor, currency
                ) VALUES (%s, %s, %s, 'course', %s, 'paid', %s, 'JOD')
                """,
                (purchase_id, user_sub, env, course.course_id, 1000),
            )
        conn.commit()
    try:
        blocked = api.delete_course(course.course_id)
        assert blocked.status_code == 409, blocked.text
        assert blocked.json().get("code") == "conflict"
    finally:
        delete_purchase_by_id(purchase_id)


def test_fulfillment_paid_grants_course_access(api: ApiClient, course_factory, lesson_factory) -> None:
    _ensure_fulfillment_importable()
    from domain_events import BillingDomainEvent  # noqa: E402
    from fulfillment_repo import process_event_in_transaction  # noqa: E402

    course = course_factory(label="integ-fulfill")
    lesson = lesson_factory(course.course_id, label="fulfill-lesson")
    assert api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id).status_code == 200
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200
    pool = resolve_student_pool_config_or_skip()
    email, password = _email(), _password()
    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    headers = {"Authorization": f"Bearer {tokens.id_token}"}
    me = api.get_users_me(headers=headers)
    student_sub = str(me.json().get("userId") or me.json().get("cognitoSub") or "")
    assert student_sub
    purchase_id = str(uuid.uuid4())
    env = billing_environment()
    provider_event_id = f"integrity:{uuid.uuid4().hex}"

    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.purchases (
                    id, user_sub, environment, product_type, course_id,
                    status, amount_minor, currency
                ) VALUES (%s, %s, %s, 'course', %s, 'pending', %s, 'JOD')
                """,
                (purchase_id, student_sub, env, course.course_id, 5000),
            )
        conn.commit()
    try:
        event = BillingDomainEvent(
            event_type="purchase.paid",
            provider="hyperpay",
            provider_event_id=provider_event_id,
            environment=env,
            user_sub=student_sub,
            plan_id="",
            payload_digest="b" * 64,
            purchase_id=purchase_id,
            product_type="course",
            amount_minor=5000,
            currency="JOD",
            provider_tran_ref="INT1",
        )
        with admin_connect() as conn:
            process_event_in_transaction(conn, event)
        assert _purchase_status(purchase_id) == "paid"
        lesson_get = api._client.get(
            f"/courses/{course.course_id}/lessons/{lesson.lesson_id}/files",
            headers=headers,
        )
        assert lesson_get.status_code == 200, lesson_get.text
    finally:
        delete_webhook_events("hyperpay", [provider_event_id])
        delete_purchase_by_id(purchase_id)
        admin_delete_cognito_user(pool["user_pool_id"], email)


def _purchase_status(purchase_id: str) -> str | None:
    with admin_connect() as conn:
        return execute_scalar(conn, "SELECT status FROM app.purchases WHERE id = %s", (purchase_id,))
