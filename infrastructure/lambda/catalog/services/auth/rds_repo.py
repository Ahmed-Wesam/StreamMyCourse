"""PostgreSQL adapter for :class:`UserProfileRepositoryPort`.

Returns dicts keyed in **camelCase** (``email``, ``role``, ``cognitoSub``,
``createdAt``, ``updatedAt``, ``userSub``) because ``UserProfileService``
accesses those exact keys. The on-disk columns are snake_case and are mapped
in ``_row_to_profile``.

``put_profile`` is an upsert: the first call inserts, and a second call (e.g.
a role promotion) updates ``email``, ``role``, ``cognito_sub``, ``updated_at``
while preserving the original ``created_at`` and any extended profile columns.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from services.auth.learning_preferences import DEFAULT_RESEARCH_INTEREST_TAGS
from services.common.db_tx import run_transaction

try:  # pragma: no cover - optional dependency path
    import psycopg2
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


ConnectionFactory = Callable[[], Any]

_PROFILE_BASE_COLUMNS = "user_sub, email, role, cognito_sub, created_at, updated_at"
_PROFILE_EXTENDED_COLUMNS = (
    "given_name, family_name, country, profession, institution, "
    "research_interests, terms_accepted_at, privacy_accepted_at"
)
_PROFILE_PREFERENCE_COLUMNS = (
    "pref_autoplay_next, pref_auto_mark_complete, pref_progress_celebrations, "
    "research_interest_tags, last_login_at"
)
_PROFILE_COLUMNS = (
    f"{_PROFILE_BASE_COLUMNS}, {_PROFILE_EXTENDED_COLUMNS}, {_PROFILE_PREFERENCE_COLUMNS}"
)


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def _bool_column(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return True


def _tags_column(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return []
    return []


def _row_to_profile(row: Tuple[Any, ...]) -> Dict[str, Any]:
    """Translate a ``users`` row tuple to the camelCase dict contract."""
    user_sub, email, role, cognito_sub, created_at, updated_at = row[:6]
    tail = list(row[6:])
    while len(tail) < 13:
        tail.append(None)
    (
        given_name,
        family_name,
        country,
        profession,
        institution,
        research_interests,
        terms_accepted_at,
        privacy_accepted_at,
    ) = tail[:8]
    pref_autoplay_next, pref_auto_mark_complete, pref_progress_celebrations, tags, last_login_at = tail[8:13]
    return {
        "userSub": str(user_sub or ""),
        "email": str(email or ""),
        "role": str(role or ""),
        "cognitoSub": str(cognito_sub or ""),
        "createdAt": _to_iso(created_at),
        "updatedAt": _to_iso(updated_at),
        "givenName": str(given_name or ""),
        "familyName": str(family_name or ""),
        "country": str(country or ""),
        "profession": str(profession or ""),
        "institution": str(institution or ""),
        "researchInterests": str(research_interests or ""),
        "termsAcceptedAt": _to_iso(terms_accepted_at),
        "privacyAcceptedAt": _to_iso(privacy_accepted_at),
        "autoplayNext": _bool_column(pref_autoplay_next),
        "autoMarkComplete": _bool_column(pref_auto_mark_complete),
        "progressCelebrations": _bool_column(pref_progress_celebrations),
        "researchInterestTags": _tags_column(tags),
        "lastLoginAt": _to_iso(last_login_at),
    }


class UserProfileRdsRepository:
    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

    def _tags_write_param(self, tags: list[str]) -> str:
        return json.dumps(tags)

    def _tags_assignment_sql(self) -> str:
        return "research_interest_tags = %s::jsonb"

    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _execute(
        self, sql: str, params: tuple = (), *, commit: bool = False
    ) -> Any:
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            return cur
        except Exception as exc:
            if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
                logger.warning("RDS connection lost, reconnecting and retrying once: %s", exc)
                self._conn = None
                conn = self._connection()
                cur = conn.cursor()
                cur.execute(sql, params)
                if commit:
                    conn.commit()
                return cur
            conn.rollback()
            raise

    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]:
        cur = self._execute(
            f"SELECT {_PROFILE_COLUMNS} FROM users WHERE user_sub = %s",
            (user_sub,),
        )
        row = cur.fetchone()
        return _row_to_profile(row) if row else None

    def get_student_active_session_id(self, user_sub: str) -> str:
        cur = self._execute(
            "SELECT student_active_session_id FROM users WHERE user_sub = %s",
            (user_sub,),
        )
        row = cur.fetchone()
        if not row:
            return ""
        return str(row[0] or "")

    def put_profile(
        self, *, user_sub: str, email: str, role: str
    ) -> Dict[str, Any]:
        # ON CONFLICT preserves ``created_at`` and extended profile columns but
        # refreshes identity fields from Cognito sync / JWT promotion.
        sql = f"""
            INSERT INTO users (user_sub, email, role, cognito_sub)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_sub) DO UPDATE
              SET email       = EXCLUDED.email,
                  role        = EXCLUDED.role,
                  cognito_sub = EXCLUDED.cognito_sub,
                  updated_at  = NOW()
            RETURNING {_PROFILE_COLUMNS}
            """

        def body() -> Dict[str, Any]:
            cur = self._execute(sql, (user_sub, email, role, user_sub), commit=False)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("INSERT users ... RETURNING returned no row")
            return _row_to_profile(row)

        return run_transaction(self._connection(), body)

    def update_profile_fields(
        self,
        *,
        user_sub: str,
        given_name: str,
        family_name: str,
        country: str,
        profession: str,
        institution: str,
        research_interests: str,
        terms_accepted_at: datetime,
        privacy_accepted_at: datetime,
    ) -> Dict[str, Any]:
        sql = f"""
            UPDATE users
               SET given_name          = %s,
                   family_name         = %s,
                   country             = %s,
                   profession          = %s,
                   institution         = %s,
                   research_interests  = %s,
                   terms_accepted_at   = %s,
                   privacy_accepted_at = %s,
                   updated_at          = NOW()
             WHERE user_sub = %s
            RETURNING {_PROFILE_COLUMNS}
            """
        params = (
            given_name,
            family_name,
            country,
            profession,
            institution,
            research_interests,
            terms_accepted_at,
            privacy_accepted_at,
            user_sub,
        )

        def body() -> Dict[str, Any]:
            cur = self._execute(sql, params, commit=False)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("UPDATE users profile ... RETURNING returned no row")
            return _row_to_profile(row)

        return run_transaction(self._connection(), body)

    def update_learning_preferences(
        self,
        *,
        user_sub: str,
        autoplay_next: bool,
        auto_mark_complete: bool,
        progress_celebrations: bool,
        research_interest_tags: list[str],
    ) -> Dict[str, Any]:
        tags_sql = self._tags_assignment_sql()
        sql = f"""
            UPDATE users
               SET pref_autoplay_next = %s,
                   pref_auto_mark_complete = %s,
                   pref_progress_celebrations = %s,
                   {tags_sql},
                   updated_at = NOW()
             WHERE user_sub = %s
            RETURNING {_PROFILE_COLUMNS}
            """
        params = (
            autoplay_next,
            auto_mark_complete,
            progress_celebrations,
            self._tags_write_param(research_interest_tags),
            user_sub,
        )

        def body() -> Dict[str, Any]:
            cur = self._execute(sql, params, commit=False)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(
                    "UPDATE users learning preferences ... RETURNING returned no row"
                )
            return _row_to_profile(row)

        return run_transaction(self._connection(), body)

    def reset_built_preferences(self, *, user_sub: str) -> Dict[str, Any]:
        tags_sql = "research_interest_tags = %s::jsonb"
        tags_param = json.dumps(list(DEFAULT_RESEARCH_INTEREST_TAGS))
        sql = f"""
            UPDATE users
               SET pref_autoplay_next = TRUE,
                   pref_auto_mark_complete = TRUE,
                   pref_progress_celebrations = TRUE,
                   {tags_sql},
                   updated_at = NOW()
             WHERE user_sub = %s
            RETURNING {_PROFILE_COLUMNS}
            """
        params = (tags_param, user_sub)

        def body() -> Dict[str, Any]:
            cur = self._execute(sql, params, commit=False)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("UPDATE users reset preferences ... RETURNING returned no row")
            return _row_to_profile(row)

        return run_transaction(self._connection(), body)

    def delete_user_row(self, user_sub: str) -> int:
        sql = "DELETE FROM users WHERE user_sub = %s"

        def body() -> int:
            cur = self._execute(sql, (user_sub,), commit=False)
            return int(cur.rowcount)

        return run_transaction(self._connection(), body)
