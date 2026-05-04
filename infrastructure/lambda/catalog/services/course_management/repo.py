from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from services.common.errors import Conflict
from services.course_management.models import Course, Lesson

try:
    import boto3
    from boto3.dynamodb.conditions import Attr, Key
except Exception:  # pragma: no cover
    boto3 = None
    Attr = None
    Key = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CourseCatalogRepository:
    def __init__(self, table_name: str):
        if not table_name:
            raise RuntimeError("TABLE_NAME is required for DynamoDB mode")
        if boto3 is None:
            raise RuntimeError("boto3 is not available")
        dynamodb = boto3.resource("dynamodb")
        self._table = dynamodb.Table(table_name)

    @staticmethod
    def _pk(course_id: str) -> str:
        return f"COURSE#{course_id}"

    @staticmethod
    def _sk_metadata() -> str:
        return "METADATA"

    @staticmethod
    def _sk_lesson(lesson_id: str) -> str:
        return f"LESSON#{lesson_id}"

    @staticmethod
    def _format_course(item: Dict[str, Any]) -> Course:
        return Course(
            id=str(item.get("PK", "")).replace("COURSE#", ""),
            title=str(item.get("title", "") or ""),
            description=str(item.get("description", "") or ""),
            status=str(item.get("status", "DRAFT") or "DRAFT"),
            createdAt=str(item.get("createdAt", "") or ""),
            updatedAt=str(item.get("updatedAt", "") or ""),
            thumbnailKey=str(item.get("thumbnailKey", "") or ""),
            createdBy=str(item.get("createdBy", "") or ""),
        )

    @staticmethod
    def _format_lesson(item: Dict[str, Any]) -> Lesson:
        # Prefer the explicit `order` attribute. Fall back to parsing a legacy
        # `LESSON#NNN` SK so pre-migration rows still render.
        if item.get("order") is not None:
            order = int(item.get("order") or 0)
        else:
            sk = str(item.get("SK", "") or "")
            sk_suffix = sk.replace("LESSON#", "")
            order = int(sk_suffix) if sk_suffix.isdigit() else 0
        return Lesson(
            id=str(item.get("lessonId", "") or ""),
            title=str(item.get("title", "") or ""),
            order=order,
            videoKey=str(item.get("videoKey", "") or ""),
            videoStatus=str(item.get("videoStatus", "pending") or "pending"),
            duration=int(item.get("duration", 0) or 0),
            thumbnailKey=str(item.get("thumbnailKey", "") or ""),
        )

    def list_courses(self) -> List[Course]:
        response = self._table.scan(
            FilterExpression=Attr("PK").begins_with("COURSE#") & Attr("SK").eq("METADATA")
        )
        return [self._format_course(i) for i in response.get("Items", [])]

    def list_courses_by_instructor(self, created_by: str) -> List[Course]:
        cb = (created_by or "").strip()
        if not cb:
            return []
        response = self._table.scan(
            FilterExpression=Attr("PK").begins_with("COURSE#")
            & Attr("SK").eq("METADATA")
            & Attr("createdBy").eq(cb)
        )
        courses = [self._format_course(i) for i in response.get("Items", [])]
        courses.sort(key=lambda c: c.createdAt or "")
        return courses

    def get_course(self, course_id: str) -> Optional[Course]:
        response = self._table.get_item(Key={"PK": self._pk(course_id), "SK": self._sk_metadata()})
        item = response.get("Item")
        return self._format_course(item) if item else None

    def create_course(self, title: str, description: str, *, created_by: str = "") -> Course:
        course_id = str(uuid4())
        now = _now_iso()
        item: Dict[str, Any] = {
            "PK": self._pk(course_id),
            "SK": self._sk_metadata(),
            "title": title,
            "description": description,
            "status": "DRAFT",
            "createdAt": now,
            "updatedAt": now,
        }
        cb = (created_by or "").strip()
        if cb:
            item["createdBy"] = cb
        self._table.put_item(Item=item)
        return self._format_course(item)

    def update_course(self, course_id: str, title: str, description: str) -> None:
        now = _now_iso()
        self._table.update_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_metadata()},
            UpdateExpression="SET title = :t, description = :d, updatedAt = :u",
            ExpressionAttributeValues={":t": title, ":d": description, ":u": now},
        )

    def set_course_status(self, course_id: str, status: str) -> None:
        now = _now_iso()
        # "status" is a DynamoDB reserved word; must use ExpressionAttributeNames.
        self._table.update_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_metadata()},
            UpdateExpression="SET #course_status = :s, updatedAt = :u",
            ExpressionAttributeNames={"#course_status": "status"},
            ExpressionAttributeValues={":s": status, ":u": now},
        )

    def set_course_thumbnail(self, course_id: str, thumbnail_key: str) -> None:
        now = _now_iso()
        self._table.update_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_metadata()},
            UpdateExpression="SET thumbnailKey = :k, updatedAt = :u",
            ExpressionAttributeValues={":k": thumbnail_key, ":u": now},
        )

    def list_lessons(self, course_id: str) -> List[Lesson]:
        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(course_id)) & Key("SK").begins_with("LESSON#"),
        )
        # SK is no longer numerically sortable (UUID-shaped); sort by `order`.
        lessons = [self._format_lesson(i) for i in response.get("Items", [])]
        lessons.sort(key=lambda l: l.order)
        return lessons

    def get_lesson_by_id(self, course_id: str, lesson_id: str) -> Optional[Lesson]:
        response = self._table.get_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)}
        )
        item = response.get("Item")
        return self._format_lesson(item) if item else None

    def create_lesson(self, course_id: str, title: str) -> Lesson:
        existing = self.list_lessons(course_id)
        next_order = max((l.order for l in existing), default=0) + 1
        lesson_id = str(uuid4())
        item = {
            "PK": self._pk(course_id),
            "SK": self._sk_lesson(lesson_id),
            "lessonId": lesson_id,
            "title": title,
            "order": next_order,
            "videoKey": "",
            "videoStatus": "pending",
            "duration": 0,
        }
        self._table.put_item(Item=item)
        return self._format_lesson(item)

    def update_lesson_title(self, course_id: str, lesson_id: str, title: str) -> None:
        self._table.update_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)},
            UpdateExpression="SET title = :t",
            ExpressionAttributeValues={":t": title},
        )

    def delete_lesson(self, course_id: str, lesson_id: str) -> None:
        self._table.delete_item(Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)})

    def delete_course_and_lessons(self, course_id: str) -> None:
        lessons = self.list_lessons(course_id)
        with self._table.batch_writer() as batch:
            batch.delete_item(Key={"PK": self._pk(course_id), "SK": self._sk_metadata()})
            for l in lessons:
                batch.delete_item(Key={"PK": self._pk(course_id), "SK": self._sk_lesson(l.id)})

    def set_lesson_video(self, course_id: str, lesson_id: str, video_key: str, status: str) -> None:
        self._table.update_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)},
            UpdateExpression="SET videoKey = :k, videoStatus = :s",
            ExpressionAttributeValues={":k": video_key, ":s": status},
        )

    def set_lesson_video_if_video_key_matches(
        self, course_id: str, lesson_id: str, video_key: str, status: str, *, expected_video_key: str
    ) -> None:
        """Atomically set lesson video key when ``videoKey`` still matches ``expected_video_key``."""
        from botocore.exceptions import ClientError

        if boto3 is None:
            raise RuntimeError("boto3 is not available")
        try:
            self._table.update_item(
                Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)},
                UpdateExpression="SET videoKey = :k, videoStatus = :s",
                ExpressionAttributeValues={
                    ":k": video_key,
                    ":s": status,
                    ":exp": expected_video_key,
                },
                ConditionExpression="videoKey = :exp",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise Conflict("Another upload started for this lesson; retry.") from exc
            raise

    def set_lesson_video_status(self, course_id: str, lesson_id: str, status: str) -> None:
        self._table.update_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)},
            UpdateExpression="SET videoStatus = :s",
            ExpressionAttributeValues={":s": status},
        )

    def set_lesson_thumbnail(self, course_id: str, lesson_id: str, thumbnail_key: str) -> None:
        self._table.update_item(
            Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)},
            UpdateExpression="SET thumbnailKey = :k",
            ExpressionAttributeValues={":k": thumbnail_key},
        )

    def set_lesson_orders(self, course_id: str, orders: Dict[str, int]) -> None:
        # Per-row updates; not atomic across rows. Safe to retry — partial
        # progress just leaves some lessons renumbered while listing still
        # works (sort by `order` is stable). Future hardening: switch to
        # TransactWriteItems (capped at 100 ops per call) if N grows.
        for lesson_id, order in orders.items():
            self._table.update_item(
                Key={"PK": self._pk(course_id), "SK": self._sk_lesson(lesson_id)},
                # `order` is a DynamoDB reserved word; alias via #order.
                UpdateExpression="SET #order = :o",
                ConditionExpression=Attr("PK").exists(),
                ExpressionAttributeNames={"#order": "order"},
                ExpressionAttributeValues={":o": int(order)},
            )
