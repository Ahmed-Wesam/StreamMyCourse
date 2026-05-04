from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserProfileRepository:
    """DynamoDB persistence for USER#<sub> profile rows (same table as catalog)."""

    def __init__(self, table_name: str) -> None:
        if not table_name:
            raise RuntimeError("TABLE_NAME is required for UserProfileRepository")
        if boto3 is None:
            raise RuntimeError("boto3 is not available")
        dynamodb = boto3.resource("dynamodb")
        self._table = dynamodb.Table(table_name)

    @staticmethod
    def _pk(user_sub: str) -> str:
        return f"USER#{user_sub}"

    @staticmethod
    def _sk_metadata() -> str:
        return "METADATA"

    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]:
        res = self._table.get_item(Key={"PK": self._pk(user_sub), "SK": self._sk_metadata()})
        return res.get("Item")

    def put_profile(
        self,
        *,
        user_sub: str,
        email: str,
        role: str,
    ) -> Dict[str, Any]:
        now = _now_iso()
        existing = self.get_profile(user_sub)
        created_at = str(existing.get("createdAt", "") or "") if existing else now
        item = {
            "PK": self._pk(user_sub),
            "SK": self._sk_metadata(),
            "userSub": user_sub,
            "email": email,
            "role": role,
            "cognitoSub": user_sub,
            "createdAt": created_at,
            "updatedAt": now,
        }
        self._table.put_item(Item=item)
        return item
