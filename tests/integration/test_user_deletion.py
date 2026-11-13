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


def _sql_purchase_count(conn, user_sub: str) -> int:
    return int(
        execute_scalar(conn, "SELECT COUNT(*) FROM app.purchases WHERE user_sub = %s", (user_sub,))
        or 0
    )


def _sql_quiz_student_counts(conn, user_sub: str) -> tuple[int, int, int]:
    bindings = int(
        execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.student_module_quiz_bindings WHERE user_sub = %s",
            (user_sub,),
        )
        or 0
    )
    attempts = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.module_quiz_attempts a
            JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
            WHERE b.user_sub = %s
            """,
            (user_sub,),
        )
        or 0
    )
    submissions = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.module_quiz_attempt_submissions s
            JOIN app.module_quiz_attempts a ON a.id = s.attempt_id
            JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
            WHERE b.user_sub = %s
            """,
            (user_sub,),
        )
        or 0
    )
    return bindings, attempts, submissions


def _mcq_options() -> list[dict[str, str]]:
    return [{"key": "A", "text": "First"}, {"key": "B", "text": "Second"}]


def _setup_published_quiz_on_first_module(
    teacher_api: ApiClient,
    course_id: str,
    *,
    served_n: int = 2,
) -> tuple[str, str]:
    mods = teacher_api.list_course_modules(course_id)
    assert mods.status_code == 200, mods.text
    module_id = str(min(mods.json(), key=lambda m: int(m["order"]))["id"])
    br = teacher_api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    assert (
        teacher_api.create_module_quiz(course_id, module_id, question_bank_id=bank_id).status_code
        == 201
    )
    for i in range(served_n):
        dr = teacher_api.create_draft_question(
            course_id,
            bank_id,
            prompt_text=f"User del Q{i + 1}?",
            options_json=_mcq_options(),
            correct_option_key="A",
        )
        assert dr.status_code == 201, dr.text
    pub = teacher_api.publish_question_bank(course_id, bank_id, n=served_n, module_id=module_id)
    assert pub.status_code == 200, pub.text
    return module_id, bank_id


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
            purchase_id = ""

            with admin_connect() as conn:
                counts = _sql_user_learning_counts(conn, user_sub)
                purchases_left = _sql_purchase_count(conn, user_sub)
            assert counts == (0, 0, 0, 0)
            assert purchases_left == 0
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


def test_operator_delete_user_clears_quiz_bindings_attempts_submissions(
    api_base_url: str,
    teacher_api: ApiClient,
) -> None:
    """Throwaway native user with a started module quiz — operator delete clears quiz rows."""
    pool = resolve_student_pool_config_or_skip()
    email = _email()
    password = _password()
    email_for_cleanup = email
    purchase_id = ""
    course_ids: list[str] = []
    course_factory = build_course_factory(teacher_api, course_ids.append)
    lesson_factory = build_lesson_factory(teacher_api)
    served_n = 2
    bank_id = ""

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

            course = course_factory(label="user-del-quiz")
            course_id = course.course_id
            module_id, bank_id = _setup_published_quiz_on_first_module(
                teacher_api, course_id, served_n=served_n
            )
            lesson = lesson_factory(course_id, label="user-del-quiz-lesson")
            assert (
                teacher_api.get_upload_url(course_id=course_id, lesson_id=lesson.lesson_id).status_code
                == 200
            )
            assert teacher_api.mark_video_ready(course_id, lesson.lesson_id).status_code == 200
            assert teacher_api.publish_course(course_id).status_code == 200

            purchase_id = insert_paid_bundle_purchase(user_sub)

            start = disposable.start_module_quiz(course_id, module_id)
            assert start.status_code == 200, start.text

            with admin_connect() as conn:
                before = _sql_quiz_student_counts(conn, user_sub)
            assert before[0] >= 1 and before[1] >= 1

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
            purchase_id = ""

            with admin_connect() as conn:
                quiz_left = _sql_quiz_student_counts(conn, user_sub)
                bank_n = int(
                    execute_scalar(
                        conn,
                        "SELECT COUNT(*) FROM app.question_banks WHERE course_id = %s AND id = %s",
                        (course_id, bank_id),
                    )
                    or 0
                )
            assert quiz_left == (0, 0, 0)
            assert bank_n == 1
    finally:
        if purchase_id:
            delete_purchase_by_id(purchase_id)
        for cid in course_ids:
            try:
                teacher_api.delete_course(cid)
            except Exception:
                pass
        if email_for_cleanup:
            admin_delete_cognito_user(cfg=pool, username=email_for_cleanup)


def _sql_assignment_student_counts(conn, user_sub: str) -> tuple[int, int, int]:
    subs = int(
        execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.assignment_submissions WHERE user_sub = %s",
            (user_sub,),
        )
        or 0
    )
    files = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*) FROM app.assignment_submission_files f
            JOIN app.assignment_submissions s ON s.id = f.submission_id
            WHERE s.user_sub = %s
            """,
            (user_sub,),
        )
        or 0
    )
    grades = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*) FROM app.assignment_grades g
            JOIN app.assignment_submissions s ON s.id = g.submission_id
            WHERE s.user_sub = %s
            """,
            (user_sub,),
        )
        or 0
    )
    return subs, files, grades


_PDF_BYTES = b"%PDF-1.4 minimal\n"
_PDF_SIZE = len(_PDF_BYTES)


def test_operator_delete_user_clears_assignment_submission_children(
    api_base_url: str,
    teacher_api: ApiClient,
    video_bucket: str,
    aws_region: str,
) -> None:
    """DSQL-7a: operator delete removes submission children and S3; assignment row stays."""
    import time

    from helpers.cleanup import s3_object_exists
    from helpers.dsql_preview_access import ensure_student_subscription
    from helpers.module_contract import require_course_modules_list

    pool = resolve_student_pool_config_or_skip()
    email = _email()
    password = _password()
    email_for_cleanup = email
    purchase_id = ""
    course_ids: list[str] = []
    course_factory = build_course_factory(teacher_api, course_ids.append)
    object_key = ""

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

            course = course_factory(label="user-del-assign")
            course_id = course.course_id
            mods = require_course_modules_list(teacher_api.list_course_modules(course_id))
            module_id = mods[0]["id"]

            created = teacher_api.create_assignment(
                course_id,
                module_id=module_id,
                title="del-test",
                pass_percent=70,
            )
            assert created.status_code == 201, created.text
            assignment_id = created.json()["assignment"]["id"]
            assert (
                teacher_api.update_assignment(
                    course_id,
                    assignment_id,
                    body={
                        "status": "published",
                        "passPercent": 70,
                        "criteria": [{"label": "Work", "maxPoints": 100}],
                    },
                ).status_code
                == 200
            )
            assert teacher_api.publish_course(course_id).status_code == 200

            ensure_student_subscription(api_base_url, disposable, course_id, module_id="")

            purchase_id = insert_paid_bundle_purchase(user_sub)

            open_sub = disposable.open_assignment_submission(course_id, assignment_id)
            assert open_sub.status_code in (200, 201), open_sub.text
            sid = open_sub.json()["submission"]["id"]

            presign = disposable.presign_submission_file(
                course_id, assignment_id, sid, title="f.pdf", file_type="pdf", byte_size=_PDF_SIZE
            )
            assert presign.status_code == 200, presign.text
            fid = presign.json()["file"]["id"]
            upload = presign.json()["upload"]
            put = httpx.put(
                upload["url"],
                content=_PDF_BYTES,
                headers={"Content-Type": "application/pdf"},
                timeout=60.0,
            )
            assert put.status_code in (200, 204), put.text
            assert (
                disposable.complete_submission_file(course_id, assignment_id, sid, fid).status_code
                == 200
            )

            with admin_connect() as conn:
                object_key = str(
                    execute_scalar(
                        conn,
                        "SELECT object_key FROM app.assignment_submission_files WHERE id = %s",
                        (fid,),
                    )
                    or ""
                )
                before = _sql_assignment_student_counts(conn, user_sub)
            assert before[0] >= 1 and before[1] >= 1
            assert object_key

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
            purchase_id = ""

            with admin_connect() as conn:
                left = _sql_assignment_student_counts(conn, user_sub)
                assign_n = int(
                    execute_scalar(
                        conn,
                        "SELECT COUNT(*) FROM app.assignments WHERE id = %s",
                        (assignment_id,),
                    )
                    or 0
                )
            assert left == (0, 0, 0)
            assert assign_n == 1

            deadline = time.monotonic() + 120.0
            while time.monotonic() < deadline:
                if not s3_object_exists(video_bucket, object_key, region=aws_region):
                    break
                time.sleep(2.0)
            assert not s3_object_exists(video_bucket, object_key, region=aws_region)
    finally:
        if purchase_id:
            delete_purchase_by_id(purchase_id)
        for cid in course_ids:
            try:
                teacher_api.delete_course(cid)
            except Exception:
                pass
        if email_for_cleanup:
            admin_delete_cognito_user(cfg=pool, username=email_for_cleanup)
