"""PostgreSQL adapter for :class:`UserProfileRepositoryPort`.

Returns dicts keyed in **camelCase** (``email``, ``role``, ``cognitoSub``,
``createdAt``, ``updatedAt``, ``userSub``) because ``UserProfileService``
accesses those exact keys. The on-disk columns are snake_case and are mapped
in ``_row_to_profile``.

``put_profile`` is an upsert: the first call inserts, and a second call (e.g.
a role promotion) updates ``email``, ``role``, ``cognito_sub``, ``updated_at``
while preserving the original ``created_at``. This mirrors the DynamoDB
adapter's behavior where ``createdAt`` is read back from the existing item.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

try:  # pragma: no cover - optional dependency path
    import psycopg2
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


ConnectionFactory = Callable[[], Any]


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def _row_to_profile(row: Tuple[Any, ...]) -> Dict[str, Any]:
    """Translate a ``users`` row tuple to the camelCase dict contract.

    Column order must match every SELECT in this module::

        user_sub, email, role, cognito_sub, created_at, updated_at
    """
    user_sub, email, role, cognito_sub, created_at, updated_at = row
    return {
        "userSub": str(user_sub or ""),
        "email": str(email or ""),
        "role": str(role or ""),
        "cognitoSub": str(cognito_sub or ""),
        "createdAt": _to_iso(created_at),
        "updatedAt": _to_iso(updated_at),
    }


_PROFILE_COLUMNS = "user_sub, email, role, cognito_sub, created_at, updated_at"


class UserProfileRdsRepository:
    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

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
            raise

    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]:
        cur = self._execute(
            f"SELECT {_PROFILE_COLUMNS} FROM users WHERE user_sub = %s",
            (user_sub,),
        )
        row = cur.fetchone()
        return _row_to_profile(row) if row else None

    def put_profile(
        self, *, user_sub: str, email: str, role: str
    ) -> Dict[str, Any]:
        # ON CONFLICT preserves ``created_at`` but refreshes the mutable fields.
        # cognito_sub mirrors user_sub today; kept as a separate column so the
        # catalog can evolve to a surrogate user_sub later without migrating.
        cur = self._execute(
            f"""
            INSERT INTO users (user_sub, email, role, cognito_sub)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_sub) DO UPDATE
              SET email       = EXCLUDED.email,
                  role        = EXCLUDED.role,
                  cognito_sub = EXCLUDED.cognito_sub,
                  updated_at  = NOW()
            RETURNING {_PROFILE_COLUMNS}
            """,
            (user_sub, email, role, user_sub),
            commit=True,
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT users ... RETURNING returned no row")
        return _row_to_profile(row)
