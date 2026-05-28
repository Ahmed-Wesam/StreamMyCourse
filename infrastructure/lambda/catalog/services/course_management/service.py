from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict
from dataclasses import asdict
from typing import Any, Dict, List
from uuid import UUID

from services.common.errors import (
    BadRequest,
    Conflict,
    Forbidden,
    NotFound,
    ServiceUnavailable,
)
from services.common.sqs_client import send_media_cleanup_job
from services.course_management.models import Course, CourseModule, Lesson
from services.course_management.ports import (
    CourseCatalogRepositoryPort,
    ImageMediaStoragePort,
    ModuleQuizVisibilityPort,
    UserProfileProvisioner,
)
from services.course_management.video_providers.kinescope_adapter import (
    KinescopeVideoMetadata,
    webhook_status_confirmed_by_api,
)
from services.course_management.video_providers.port import (
    KinescopePlayback,
    S3Playback,
    VideoPlayback,
    VideoProviderPort,
)
from services.subscription.ports import CourseAccessPort

logger = logging.getLogger(__name__)


def _is_valid_uuid(value: str) -> bool:
    """Check if value is a valid UUID format."""
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


class CourseManagementService:
    def __init__(
        self,
        repo: CourseCatalogRepositoryPort,
        image_storage: ImageMediaStoragePort | None,
        *,
        video_provider: VideoProviderPort | None = None,
        course_access: CourseAccessPort,
        media_cleanup_queue_url: str = "",
        module_quiz_visibility: ModuleQuizVisibilityPort | None = None,
        kinescope_drm_jwt_secret: str = "",
        kinescope_drm_jwt_issuer: str = "streammycourse",
        kinescope_drm_jwt_audience: str = "kinescope",
        kinescope_api_token: str = "",
        deployment_environment: str = "dev",
    ):
        self._repo = repo
        self._image_storage = image_storage
        self._video_provider = video_provider
        self._course_access = course_access
        self._media_cleanup_queue_url = (media_cleanup_queue_url or "").strip()
        self._module_quiz_visibility = module_quiz_visibility
        self._kinescope_drm_jwt_secret = (kinescope_drm_jwt_secret or "").strip()
        self._kinescope_drm_jwt_issuer = (kinescope_drm_jwt_issuer or "").strip()
        self._kinescope_drm_jwt_audience = (kinescope_drm_jwt_audience or "").strip()
        self._kinescope_api_token = (kinescope_api_token or "").strip()
        self._deployment_environment = (deployment_environment or "dev").strip().lower()

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        padding = "=" * ((4 - len(data) % 4) % 4)
        return base64.urlsafe_b64decode(f"{data}{padding}")

    def mint_kinescope_drm_jwt(
        self,
        *,
        sub: str,
        video_id: str,
        role: str = "student",
        expires_in_seconds: int = 300,
    ) -> str:
        if not self._kinescope_drm_jwt_secret:
            raise BadRequest("Kinescope DRM JWT secret is not configured")
        now = int(time.time())
        normalized_role = (role or "student").strip().lower() or "student"
        payload = {
            "sub": sub,
            "video_id": video_id,
            "role": normalized_role,
            "iss": self._kinescope_drm_jwt_issuer,
            "aud": self._kinescope_drm_jwt_audience,
            "iat": now,
            "exp": now + max(1, int(expires_in_seconds)),
        }
        header = {"alg": "HS256", "typ": "JWT"}
        signing_input = (
            f"{self._b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
            f"{self._b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
        )
        signature = hmac.new(
            self._kinescope_drm_jwt_secret.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{signing_input}.{self._b64url_encode(signature)}"

    def _verify_kinescope_drm_jwt(self, token: str) -> Dict[str, Any] | None:
        if not self._kinescope_drm_jwt_secret:
            return None
        parts = (token or "").split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        try:
            signing_input = f"{header_b64}.{payload_b64}"
            expected_signature = hmac.new(
                self._kinescope_drm_jwt_secret.encode("utf-8"),
                signing_input.encode("ascii"),
                hashlib.sha256,
            ).digest()
            actual_signature = self._b64url_decode(signature_b64)
            if not hmac.compare_digest(actual_signature, expected_signature):
                return None
            payload = json.loads(self._b64url_decode(payload_b64).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        now = int(time.time())
        exp = int(payload.get("exp", 0) or 0)
        if exp <= now:
            return None
        if payload.get("iss") != self._kinescope_drm_jwt_issuer:
            return None
        if payload.get("aud") != self._kinescope_drm_jwt_audience:
            return None
        if not str(payload.get("sub") or "").strip():
            return None
        if not str(payload.get("video_id") or "").strip():
            return None
        return payload

    def _delete_media_keys(self, keys: List[str]) -> None:
        if self._image_storage is None:
            return
        deduped = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
        if not deduped:
            return
        try:
            self._image_storage.delete_objects(deduped)
        except Exception as exc:
            logger.warning("S3 delete_objects failed (continuing): %s", exc)

    @staticmethod
    def _split_cleanup_targets(course_id: str, keys: List[str]) -> tuple[List[str], List[str]]:
        s3_keys: List[str] = []
        kinescope_video_ids: List[str] = []
        prefix = f"{course_id}/"
        for raw in keys:
            key = (raw or "").strip()
            if not key:
                continue
            if key.startswith(prefix):
                s3_keys.append(key)
            else:
                kinescope_video_ids.append(key)
        return (
            list(dict.fromkeys(s3_keys)),
            list(dict.fromkeys(kinescope_video_ids)),
        )

    def _safe_presign_get(self, key: str, *, media: str) -> str | None:
        """Presign GET for display URLs, or None if the key cannot be signed.

        One bad or legacy S3 key must not fail entire list endpoints (for example
        ``GET /courses/{id}/lessons``) for every lesson in the course.
        """
        if self._image_storage is None:
            return None
        k = (key or "").strip()
        if not k:
            return None
        try:
            return self._image_storage.presign_get(key=k, expires_seconds=3600)
        except BadRequest:
            logger.warning("presign_get rejected key for %s", media, extra={"key_prefix": k[:96]})
            return None
        except Exception as exc:  # pragma: no cover - botocore / network edge paths
            logger.warning("presign_get failed for %s: %s", media, exc, extra={"key_prefix": k[:96]})
            return None

    def _public_course_dict(self, course: Course) -> Dict[str, Any]:
        data = asdict(course)
        thumb_key = (data.pop("thumbnailKey", None) or "").strip()
        if thumb_key and self._image_storage is not None:
            url = self._safe_presign_get(thumb_key, media="course_thumbnail")
            if url:
                data["thumbnailUrl"] = url
        return data

    def _apply_course_cover_fallback(self, course_id: str, public: Dict[str, Any]) -> None:
        """When no course cover is set, use the first lesson thumbnail (by order) for catalog/hero."""
        if public.get("thumbnailUrl") or self._image_storage is None:
            return
        lessons = self._repo.list_lessons(course_id)
        for lesson in sorted(lessons, key=lambda l: (l.moduleOrder, l.order)):
            tk = (lesson.thumbnailKey or "").strip()
            if tk:
                url = self._safe_presign_get(tk, media="lesson_thumbnail_fallback")
                if url:
                    public["thumbnailUrl"] = url
                    return

    @staticmethod
    def _validate_thumbnail_key(course_id: str, thumbnail_key: str) -> None:
        prefix = f"{course_id}/thumbnail/"
        if not thumbnail_key.startswith(prefix):
            raise BadRequest("Invalid thumbnail key")

    @staticmethod
    def _validate_lesson_thumbnail_key(course_id: str, lesson_id: str, thumbnail_key: str) -> None:
        prefix = f"{course_id}/lessons/{lesson_id}/thumbnail/"
        if not thumbnail_key.startswith(prefix):
            raise BadRequest("Invalid lesson thumbnail key")

    def _public_lesson_dict(self, lesson: Lesson) -> Dict[str, Any]:
        data = asdict(lesson)
        data.pop("videoKey", None)
        thumb_key = (data.pop("thumbnailKey", None) or "").strip()
        if thumb_key and self._image_storage is not None:
            url = self._safe_presign_get(thumb_key, media="lesson_thumbnail")
            if url:
                data["thumbnailUrl"] = url
        return data

    def list_published_courses(self) -> List[Dict[str, Any]]:
        courses = self._repo.list_courses()
        published = [c for c in courses if c.status == "PUBLISHED"]
        out: List[Dict[str, Any]] = []
        for c in published:
            data = self._public_course_dict(c)
            self._apply_course_cover_fallback(c.id, data)
            out.append(data)
        return out

    def list_instructor_courses(
        self,
        *,
        cognito_sub: str,
        role: str,
    ) -> List[Dict[str, Any]]:
        """Courses for the instructor dashboard (draft + published), scoped by owner unless admin."""
        sub = (cognito_sub or "").strip()
        # Authentication (non-empty sub) is enforced at the controller boundary.
        if not self._teacher_or_admin(role):
            raise Forbidden("Teacher or admin role required")
        if self._is_admin(role):
            courses = self._repo.list_courses()
        else:
            courses = self._repo.list_courses_by_instructor(sub)
        out: List[Dict[str, Any]] = []
        for c in courses:
            data = self._public_course_dict(c)
            self._apply_course_cover_fallback(c.id, data)
            out.append(data)
        return out

    def get_course(self, course_id: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        data = self._public_course_dict(course)
        self._apply_course_cover_fallback(course_id, data)
        return data

    @staticmethod
    def _norm_role(role: str) -> str:
        return (role or "").strip().lower()

    def _is_admin(self, role: str) -> bool:
        return self._norm_role(role) == "admin"

    def _teacher_or_admin(self, role: str) -> bool:
        return self._norm_role(role) in ("teacher", "admin")

    def _can_manage_course_unenrolled(self, course: Course, *, cognito_sub: str, role: str) -> bool:
        """Admin or instructor with modify rights (same ownership rule as mutations)."""
        if self._is_admin(role):
            return True
        if not self._teacher_or_admin(role):
            return False
        owner = (course.createdBy or "").strip()
        if not owner:
            logger.warning("course %s has blank createdBy — denying modify", course.id)
            return False
        return owner == cognito_sub.strip()

    def viewer_has_lesson_access(
        self,
        course: Course,
        *,
        course_id: str,
        cognito_sub: str,
        role: str,
    ) -> bool:
        return self._course_access.has_course_access(
            cognito_sub, course_id, role, course=course
        )

    def ensure_can_view_lessons_and_playback(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Course:
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if self.viewer_has_lesson_access(course, course_id=course_id, cognito_sub=cognito_sub, role=role):
            return course
        raise Forbidden(
            "Subscription required to view this course",
            code="subscription_required",
        )

    def get_course_detail_with_enrollment(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if course.status == "DRAFT":
            if not self._can_manage_course_unenrolled(course, cognito_sub=cognito_sub, role=role):
                raise NotFound("Course not found")
        has_access = self.viewer_has_lesson_access(
            course, course_id=course_id, cognito_sub=cognito_sub, role=role
        )
        data = self._public_course_dict(course)
        self._apply_course_cover_fallback(course_id, data)
        data["hasAccess"] = bool(has_access)
        data["enrolled"] = bool(has_access)
        return data

    def enroll_in_published_course(self, course_id: str, *, cognito_sub: str) -> Dict[str, Any]:
        sub = (cognito_sub or "").strip()
        if not sub:
            raise BadRequest("cognito_sub must not be empty")
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course or course.status != "PUBLISHED":
            raise NotFound("Course not found")
        raise Forbidden(
            "Subscription required to access this course",
            code="subscription_required",
        )

    def enroll_in_published_course_with_profile(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        email: str,
        role: str,
        profile_provisioner: UserProfileProvisioner,
    ) -> Dict[str, Any]:
        del email, role, profile_provisioner  # enroll deprecated; auth at controller
        return self.enroll_in_published_course(course_id, cognito_sub=cognito_sub)

    def create_course(
        self,
        title: str,
        description: str,
        *,
        created_by: str,
        role: str = "",
    ) -> Dict[str, Any]:
        sub = (created_by or "").strip()
        # Authentication is enforced at the controller boundary.
        if not self._teacher_or_admin(role):
            raise Forbidden("Teacher or admin role required")
        if not sub:
            raise BadRequest("created_by must not be empty")
        course = self._repo.create_course(
            title=title or "Untitled Course",
            description=description or "",
            created_by=sub,
        )
        return {"id": course.id, "status": course.status}

    def ensure_can_modify_course(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> None:
        """When auth is enforced, only teacher/admin may mutate; admin bypasses ownership."""
        sub = (cognito_sub or "").strip()
        if not sub:
            raise BadRequest("cognito_sub must not be empty")
        r = (role or "").strip().lower()
        if r == "admin":
            return
        if r not in ("teacher", "admin"):
            raise Forbidden("Teacher or admin role required")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        owner = (course.createdBy or "").strip()
        if not owner:
            raise BadRequest("Course has no owner (created_by is blank)")
        if owner != sub:
            raise Forbidden("Not allowed to modify this course")

    def ensure_publisher_question_bank_read(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> None:
        """Publisher-only question-bank reads: same manage predicate as draft modules; 404 on denial."""
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if not self._can_manage_course_unenrolled(
            course, cognito_sub=cognito_sub, role=role
        ):
            raise NotFound("Course not found")

    def update_course(self, course_id: str, title: str, description: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        self._repo.update_course(course_id=course_id, title=title, description=description)
        return {"id": course_id, "updated": True}

    def delete_course(self, course_id: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        keys: List[str] = []
        if course.thumbnailKey.strip():
            keys.append(course.thumbnailKey.strip())
        for lesson in self._repo.list_lessons(course_id):
            if lesson.videoKey.strip():
                keys.append(lesson.videoKey.strip())
            if lesson.thumbnailKey.strip():
                keys.append(lesson.thumbnailKey.strip())
        deduped = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
        if deduped and not self._media_cleanup_queue_url:
            raise ServiceUnavailable(
                "Media cleanup queue is not configured (MEDIA_CLEANUP_QUEUE_URL is empty)"
            )
        # Remove DB rows first so catalog reflects the delete even if S3 cleanup lags (async worker).
        self._repo.delete_course_and_lessons(course_id)
        if deduped:
            s3_keys, kinescope_video_ids = self._split_cleanup_targets(course_id, deduped)
            send_media_cleanup_job(
                self._media_cleanup_queue_url,
                course_id,
                deduped,
                s3_keys=s3_keys,
                kinescope_video_ids=kinescope_video_ids,
            )
        return {"id": course_id, "deleted": True}

    def list_lessons(self, course_id: str) -> List[Dict[str, Any]]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        return [self._public_lesson_dict(l) for l in self._repo.list_lessons(course_id)]

    def list_lessons_public(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> List[Dict[str, Any]]:
        """Published lesson rows for catalog UI (thumbnails, no videoKey). DRAFT is 404 unless caller can manage."""
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if course.status == "DRAFT":
            if not self._can_manage_course_unenrolled(course, cognito_sub=cognito_sub, role=role):
                raise NotFound("Course not found")
        lessons = self._repo.list_lessons(course_id)
        return [
            self._public_lesson_dict(l) for l in sorted(lessons, key=lambda x: (x.moduleOrder, x.order))
        ]

    def _resolve_module_for_new_lesson(self, course_id: str, module_id: str | None) -> str:
        mid = (module_id or "").strip()
        if mid:
            if not _is_valid_uuid(mid):
                raise NotFound("Module not found")
            mod = self._repo.get_course_module(course_id, mid)
            if not mod:
                raise NotFound("Module not found")
            return mod.id
        modules = self._repo.list_course_modules(course_id)
        if not modules:
            raise BadRequest("Course has no modules")
        return modules[0].id

    def list_course_modules_public(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> List[Dict[str, Any]]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if course.status == "DRAFT":
            if not self._can_manage_course_unenrolled(course, cognito_sub=cognito_sub, role=role):
                raise NotFound("Course not found")
        visibility: Dict[str, Dict[str, Any]] = {}
        if self._module_quiz_visibility is not None:
            has_lesson_access = self.viewer_has_lesson_access(
                course,
                course_id=course_id,
                cognito_sub=cognito_sub,
                role=role,
            )
            visibility = self._module_quiz_visibility.module_quiz_visibility_by_course(
                course_id,
                course_status=course.status,
                has_lesson_access=has_lesson_access,
                cognito_sub=cognito_sub,
            )
        return [
            self._public_module_dict(m, module_quiz=visibility.get(m.id))
            for m in self._repo.list_course_modules(course_id)
        ]

    @staticmethod
    def _public_module_dict(
        m: CourseModule,
        *,
        module_quiz: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "order": m.order,
            "createdAt": m.createdAt,
            "updatedAt": m.updatedAt,
        }
        if module_quiz is not None:
            row["moduleQuiz"] = module_quiz
        return row

    def create_course_module(self, course_id: str, title: str, description: str = "") -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        m = self._repo.create_course_module(course_id, title or "Untitled module", description or "")
        return {"moduleId": m.id, "order": m.order}

    def delete_course_module(self, course_id: str, module_id: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(module_id):
            raise NotFound("Module not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        modules = self._repo.list_course_modules(course_id)
        if module_id not in {m.id for m in modules}:
            return {"moduleId": module_id, "deleted": False}
        if len(modules) <= 1:
            raise BadRequest("Cannot delete the last module in a course")
        lesson_rows = [
            l
            for l in self._repo.list_lessons(course_id)
            if l.moduleId == module_id
        ]
        media_keys: List[str] = []
        for lesson in lesson_rows:
            if lesson.videoKey.strip():
                media_keys.append(lesson.videoKey.strip())
            if lesson.thumbnailKey.strip():
                media_keys.append(lesson.thumbnailKey.strip())
        deduped = list(dict.fromkeys(k.strip() for k in media_keys if k and k.strip()))
        if deduped and not self._media_cleanup_queue_url:
            raise ServiceUnavailable(
                "Media cleanup queue is not configured (MEDIA_CLEANUP_QUEUE_URL is empty)"
            )
        self._repo.delete_course_module(course_id, module_id)
        if deduped:
            s3_keys, kinescope_video_ids = self._split_cleanup_targets(course_id, deduped)
            send_media_cleanup_job(
                self._media_cleanup_queue_url,
                course_id,
                deduped,
                s3_keys=s3_keys,
                kinescope_video_ids=kinescope_video_ids,
            )
        return {"moduleId": module_id, "deleted": True}

    def create_lesson(
        self, course_id: str, title: str, *, module_id: str | None = None
    ) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        resolved_module = self._resolve_module_for_new_lesson(course_id, module_id)
        lesson = self._repo.create_lesson(
            course_id=course_id, module_id=resolved_module, title=title or "Lesson"
        )
        return {"lessonId": lesson.id, "moduleId": lesson.moduleId, "order": lesson.order}

    def update_lesson(self, course_id: str, lesson_id: str, title: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        self._repo.update_lesson_title(course_id=course_id, lesson_id=lesson_id, title=title or lesson.title)
        return {"lessonId": lesson_id, "updated": True}

    def delete_lesson(self, course_id: str, lesson_id: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        media_keys: List[str] = []
        if lesson.videoKey.strip():
            media_keys.append(lesson.videoKey.strip())
        if lesson.thumbnailKey.strip():
            media_keys.append(lesson.thumbnailKey.strip())
        deduped = list(dict.fromkeys(k.strip() for k in media_keys if k and k.strip()))
        if deduped and not self._media_cleanup_queue_url:
            raise ServiceUnavailable(
                "Media cleanup queue is not configured (MEDIA_CLEANUP_QUEUE_URL is empty)"
            )
        self._repo.delete_lesson(course_id=course_id, lesson_id=lesson_id)
        if deduped:
            s3_keys, kinescope_video_ids = self._split_cleanup_targets(course_id, deduped)
            send_media_cleanup_job(
                self._media_cleanup_queue_url,
                course_id,
                deduped,
                s3_keys=s3_keys,
                kinescope_video_ids=kinescope_video_ids,
            )
        # Compact remaining orders to 1..N within each module.
        remaining = self._repo.list_lessons(course_id)
        by_module: defaultdict[str, List[Lesson]] = defaultdict(list)
        for lesson in remaining:
            by_module[lesson.moduleId].append(lesson)
        mapping: Dict[str, int] = {}
        for grp in by_module.values():
            for i, lesson in enumerate(sorted(grp, key=lambda l: l.order)):
                next_order = i + 1
                if lesson.order != next_order and lesson.id:
                    mapping[lesson.id] = next_order
        if mapping:
            self._repo.set_lesson_orders(course_id, mapping)
        return {"lessonId": lesson_id, "deleted": True}

    def publish_course(self, course_id: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        lessons = self._repo.list_lessons(course_id)
        if not any(l.videoStatus == "ready" for l in lessons):
            raise BadRequest("Course needs at least one ready lesson to publish")
        self._repo.set_course_status(course_id, "PUBLISHED")
        return {"id": course_id, "status": "PUBLISHED"}

    def mark_lesson_video_ready(
        self,
        course_id: str,
        lesson_id: str,
        *,
        thumbnail_key: str | None = None,
    ) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        if not lesson.videoKey:
            raise BadRequest("No video uploaded for lesson")
        if thumbnail_key:
            self._validate_lesson_thumbnail_key(course_id, lesson_id, thumbnail_key)
            old_thumb = lesson.thumbnailKey.strip()
            if old_thumb and old_thumb != thumbnail_key.strip():
                self._delete_media_keys([old_thumb])
            self._repo.set_lesson_thumbnail(course_id, lesson_id, thumbnail_key)
        if (
            self._video_provider is not None
            and not self._video_provider.marks_ready_on_upload_complete
        ):
            return self._mark_async_provider_lesson_ready(
                course_id,
                lesson_id,
                video_key=lesson.videoKey,
            )
        self._repo.set_lesson_video_status(course_id=course_id, lesson_id=lesson_id, status="ready")
        return {"lessonId": lesson_id, "videoStatus": "ready"}

    def _apply_kinescope_ready_metadata(
        self,
        course_id: str,
        lesson_id: str,
        metadata: KinescopeVideoMetadata,
    ) -> Dict[str, Any]:
        self._repo.set_lesson_video_status(course_id=course_id, lesson_id=lesson_id, status="ready")
        response: Dict[str, Any] = {"lessonId": lesson_id, "videoStatus": "ready"}
        duration = metadata.duration_seconds
        if duration is not None:
            try:
                self._repo.set_lesson_duration(course_id, lesson_id, duration)
            except Exception:
                logger.warning(
                    "kinescope ready failed to persist duration course=%s lesson=%s",
                    course_id,
                    lesson_id,
                    exc_info=True,
                )
            response["duration"] = duration
        return response

    def _mark_async_provider_lesson_ready(
        self,
        course_id: str,
        lesson_id: str,
        *,
        video_key: str,
        provider_metadata: KinescopeVideoMetadata | None = None,
        provider_metadata_supplied: bool | None = None,
    ) -> Dict[str, Any]:
        """Kinescope (async transcode): require edge-verified metadata in prod; dev allows bypass."""
        metadata: KinescopeVideoMetadata | None = provider_metadata
        if metadata is not None and webhook_status_confirmed_by_api(
            "done", metadata.status
        ):
            return self._apply_kinescope_ready_metadata(course_id, lesson_id, metadata)
        if self._deployment_environment == "prod":
            raise BadRequest("Video is still processing")
        logger.warning(
            "mark_lesson_video_ready dev bypass without Kinescope done confirmation "
            "course=%s lesson=%s video_key=%s",
            course_id,
            lesson_id,
            video_key,
        )
        self._repo.set_lesson_video_status(course_id=course_id, lesson_id=lesson_id, status="ready")
        return {"lessonId": lesson_id, "videoStatus": "ready"}

    def prepare_lesson_video_mark_ready(
        self,
        *,
        course_id: str,
        lesson_id: str,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        self.ensure_can_modify_course(
            course_id,
            cognito_sub=cognito_sub,
            role=role,
        )
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        if not lesson.videoKey:
            raise BadRequest("No video uploaded for lesson")
        return {
            "courseId": course_id,
            "lessonId": lesson_id,
            "videoKey": lesson.videoKey.strip(),
        }

    def apply_lesson_video_mark_ready(
        self,
        *,
        course_id: str,
        lesson_id: str,
        video_key: str,
        cognito_sub: str,
        role: str,
        thumbnail_key: str | None = None,
        provider_metadata: KinescopeVideoMetadata | None = None,
        provider_metadata_supplied: bool | None = None,
    ) -> Dict[str, Any]:
        self.ensure_can_modify_course(
            course_id,
            cognito_sub=cognito_sub,
            role=role,
        )
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        if not lesson.videoKey:
            raise BadRequest("No video uploaded for lesson")
        if video_key.strip() != lesson.videoKey.strip():
            raise BadRequest("Video key mismatch")
        if thumbnail_key:
            self._validate_lesson_thumbnail_key(course_id, lesson_id, thumbnail_key)
            old_thumb = lesson.thumbnailKey.strip()
            if old_thumb and old_thumb != thumbnail_key.strip():
                self._delete_media_keys([old_thumb])
            self._repo.set_lesson_thumbnail(course_id, lesson_id, thumbnail_key)
        if (
            self._video_provider is not None
            and not self._video_provider.marks_ready_on_upload_complete
        ):
            return self._mark_async_provider_lesson_ready(
                course_id,
                lesson_id,
                video_key=video_key,
                provider_metadata=provider_metadata,
                provider_metadata_supplied=provider_metadata_supplied,
            )
        self._repo.set_lesson_video_status(course_id=course_id, lesson_id=lesson_id, status="ready")
        return {"lessonId": lesson_id, "videoStatus": "ready"}

    def get_playback_url(
        self,
        course_id: str,
        lesson_id: str,
        *,
        cognito_sub: str = "",
        role: str = "student",
    ) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        if lesson.videoStatus != "ready":
            raise BadRequest("Video not ready")
        if not lesson.videoKey:
            raise NotFound("No video uploaded")
        if self._video_provider is None:
            raise BadRequest("Playback is not configured")
        playback = self._video_provider.resolve_playback(
            video_key=lesson.videoKey, expires_seconds=3600
        )
        return self._playback_to_api(
            playback,
            cognito_sub=(cognito_sub or "").strip(),
            role=(role or "student").strip().lower() or "student",
        )

    def _playback_to_api(
        self,
        playback: VideoPlayback,
        *,
        cognito_sub: str,
        role: str = "student",
    ) -> Dict[str, Any]:
        if isinstance(playback, S3Playback):
            return {"provider": "s3", "playbackUrl": playback.playback_url}
        if isinstance(playback, KinescopePlayback):
            drm_token = (playback.drm_auth_token or "").strip()
            if not drm_token:
                drm_token = self.mint_kinescope_drm_jwt(
                    sub=cognito_sub,
                    video_id=playback.video_id,
                    role=role,
                )
            return {
                "provider": "kinescope",
                "videoId": playback.video_id,
                "drmAuthToken": drm_token,
            }
        raise BadRequest("Unsupported playback response from video provider")

    def authorize_kinescope_drm(self, payload: Dict[str, Any]) -> bool:
        token = str(payload.get("token") or "").strip()
        requested_video_id = str(
            payload.get("videoId") or payload.get("video_id") or ""
        ).strip()
        claims = self._verify_kinescope_drm_jwt(token)
        if claims is None:
            return False
        token_video_id = str(claims.get("video_id") or "").strip()
        if not requested_video_id or token_video_id != requested_video_id:
            return False
        loc = self._repo.find_lesson_by_video_key(token_video_id)
        if loc is None:
            return False
        course_id, _lesson_id = loc
        course = self._repo.get_course(course_id)
        if course is None:
            return False
        sub = str(claims.get("sub") or "").strip()
        role = str(claims.get("role") or "student").strip().lower() or "student"
        return self.viewer_has_lesson_access(
            course,
            course_id=course_id,
            cognito_sub=sub,
            role=role,
        )

    def prepare_lesson_video_upload(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        filesize: int | None,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        self.ensure_can_modify_course(
            course_id,
            cognito_sub=cognito_sub,
            role=role,
        )
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        return {
            "courseId": course_id,
            "lessonId": lesson_id,
            "filename": filename,
            "contentType": content_type,
            "filesize": filesize,
            "expectedVideoKey": (lesson.videoKey or "").strip(),
        }

    def commit_pending_lesson_video_upload(
        self,
        *,
        course_id: str,
        lesson_id: str,
        video_key: str,
        expected_video_key: str,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        self.ensure_can_modify_course(
            course_id,
            cognito_sub=cognito_sub,
            role=role,
        )
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        self._repo.set_lesson_video_if_video_key_matches(
            course_id=course_id,
            lesson_id=lesson_id,
            video_key=video_key,
            status="pending",
            expected_video_key=expected_video_key,
        )
        return {"committed": True}

    def get_upload_url(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        filesize: int | None = None,
    ) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        if self._video_provider is None:
            raise BadRequest("Uploads are not configured")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        expected_key = (lesson.videoKey or "").strip()
        init = self._video_provider.init_lesson_upload(
            course_id=course_id,
            lesson_id=lesson_id,
            filename=filename,
            content_type=content_type,
            filesize=filesize,
        )
        try:
            self._repo.set_lesson_video_if_video_key_matches(
                course_id=course_id,
                lesson_id=lesson_id,
                video_key=init.video_key,
                status="pending",
                expected_video_key=expected_key,
            )
        except Conflict:
            self._video_provider.delete_videos([init.video_key])
            raise
        # Do not delete `expected_key` here: a second presign can race with a client
        # still uploading to the first URL. Orphan prior objects are acceptable for MVP;
        # cleanup can be lifecycle or a later sweeper keyed off DB.
        return {
            "uploadUrl": init.upload_url,
            "videoKey": init.video_key,
            "uploadMethod": init.upload_method,
            "provider": self._video_provider.provider_id,
        }

    def get_thumbnail_upload_url(
        self,
        *,
        course_id: str,
        filename: str,
        content_type: str,
    ) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if self._image_storage is None:
            raise BadRequest("Uploads are not configured")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        # Do not delete the existing S3 object here: the DB still points at it until
        # mark_course_thumbnail_ready runs. Deleting early breaks thumbnails if the
        # PUT fails or the client never calls thumbnail-ready.
        presign = self._image_storage.presign_thumbnail_put(
            course_id=course_id,
            filename=filename,
            content_type=content_type,
        )
        return {"uploadUrl": presign.uploadUrl, "thumbnailKey": presign.videoKey}

    def get_lesson_thumbnail_upload_url(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
    ) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")
        if self._image_storage is None:
            raise BadRequest("Uploads are not configured")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        # Same as course thumbnails: keep the old object until mark_lesson_video_ready
        # persists the new key (that path deletes the previous key from S3).
        presign = self._image_storage.presign_lesson_thumbnail_put(
            course_id=course_id,
            lesson_id=lesson_id,
            filename=filename,
            content_type=content_type,
        )
        return {"uploadUrl": presign.uploadUrl, "thumbnailKey": presign.videoKey}

    def mark_course_thumbnail_ready(self, course_id: str, thumbnail_key: str) -> Dict[str, Any]:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        self._validate_thumbnail_key(course_id, thumbnail_key)
        old_thumb = course.thumbnailKey.strip()
        if old_thumb and old_thumb != thumbnail_key.strip():
            self._delete_media_keys([old_thumb])
        self._repo.set_course_thumbnail(course_id, thumbnail_key)
        return {"id": course_id, "thumbnailReady": True}

    def handle_kinescope_media_status(
        self,
        payload: Dict[str, Any],
        *,
        verified_metadata: KinescopeVideoMetadata | None = None,
        verified_metadata_supplied: bool = False,
    ) -> Dict[str, Any]:
        event_type = str(payload.get("event") or "").strip()
        if event_type != "media.update.status":
            raise BadRequest("Unsupported Kinescope webhook event")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise BadRequest("Invalid Kinescope webhook payload")

        video_id = str(data.get("id") or "").strip()
        if not video_id:
            raise BadRequest("Missing Kinescope video id")

        status = str(data.get("status") or "").strip().lower()
        loc = self._repo.find_lesson_by_video_key(video_id)
        if loc is None:
            logger.info(
                "kinescope webhook ignored unknown video_id=%s status=%s",
                video_id,
                status,
            )
            return {"ignored": True}

        course_id, lesson_id = loc
        resolved_metadata: KinescopeVideoMetadata | None = None
        if status in ("done", "error", "aborted"):
            if verified_metadata_supplied:
                if verified_metadata is None:
                    logger.warning(
                        "kinescope webhook rejected mutating event without verified metadata video_id=%s status=%s",
                        video_id,
                        status,
                    )
                    return {"ignored": True, "reason": "verification_failed"}
                if not webhook_status_confirmed_by_api(status, verified_metadata.status):
                    logger.warning(
                        "kinescope webhook status mismatch video_id=%s webhook=%s api=%s",
                        video_id,
                        status,
                        verified_metadata.status,
                    )
                    return {"ignored": True, "reason": "status_mismatch"}
                resolved_metadata = verified_metadata
            else:
                logger.warning(
                    "kinescope webhook rejected mutating event without edge-verified metadata "
                    "video_id=%s status=%s",
                    video_id,
                    status,
                )
                return {"ignored": True, "reason": "verification_unconfigured"}

        if status == "done":
            assert resolved_metadata is not None
            return {
                "courseId": course_id,
                "lessonId": lesson_id,
                **self._apply_kinescope_ready_metadata(
                    course_id, lesson_id, resolved_metadata
                ),
            }
        if status in ("error", "aborted"):
            self._repo.set_lesson_video_status(course_id, lesson_id, "failed")
            return {
                "courseId": course_id,
                "lessonId": lesson_id,
                "videoStatus": "failed",
            }

        logger.info(
            "kinescope webhook no-op course=%s lesson=%s video_id=%s status=%s",
            course_id,
            lesson_id,
            video_id,
            status,
        )
        return {
            "courseId": course_id,
            "lessonId": lesson_id,
            "videoStatus": status or "pending",
        }

