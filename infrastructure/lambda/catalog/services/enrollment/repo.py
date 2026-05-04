from __future__ import annotations

from datetime import datetime, timezone

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EnrollmentRepository:
    """DynamoDB: PK=USER#<sub>, SK=ENROLLMENT#<courseId>."""

    def __init__(self, table_name: str) -> None:
        if not table_name:
            raise RuntimeError("TABLE_NAME is required for EnrollmentRepository")
        if boto3 is None:
            raise RuntimeError("boto3 is not available")
        dynamodb = boto3.resource("dynamodb")
        self._table = dynamodb.Table(table_name)

    @staticmethod
    def _pk(user_sub: str) -> str:
        return f"USER#{user_sub}"

    @staticmethod
    def _sk(course_id: str) -> str:
        return f"ENROLLMENT#{course_id}"

    def has_enrollment(self, *, user_sub: str, course_id: str) -> bool:
        res = self._table.get_item(Key={"PK": self._pk(user_sub), "SK": self._sk(course_id)})
        return bool(res.get("Item"))

    def put_enrollment(self, *, user_sub: str, course_id: str, source: str = "self_service") -> None:
        self._table.put_item(
            Item={
                "PK": self._pk(user_sub),
                "SK": self._sk(course_id),
                "courseId": course_id,
                "userSub": user_sub,
                "enrolledAt": _now_iso(),
                "source": source,
            }
        )
