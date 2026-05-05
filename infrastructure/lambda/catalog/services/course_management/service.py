from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List

from services.common.errors import BadRequest, Conflict, Forbidden, NotFound
from services.course_management.models import Course, Lesson
from services.course_management.ports import CourseCatalogRepositoryPort, CourseMediaStoragePort
from services.enrollment.ports import EnrollmentRepositoryPort

logger = logging.getLogger(__name__)


class CourseManagementService:
    def __init__(
        self,
        repo: CourseCatalogRepositoryPort,
        storage: CourseMediaStoragePort | None,
        enrollments: EnrollmentRepositoryPort,
        *,
        cloudfront_signer: Any | None = None,
        cf_invalidator: Any | None = None,
        media_get_expires_seconds: int = 28800,
    ):
        self._repo = repo
        self._storage = storage
        self._enrollments = enrollments
        self._cloudfront_signer = cloudfront_signer
        self._cf_invalidator = cf_invalidator
        self._media_get_expires_seconds = max(60, int(media_get_expires_seconds))

    def _delete_media_keys(self, keys: List[str]) -> None:
        if self._storage is None:
            return
        deduped = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
        if not deduped:
            return
        try:
            self._storage.delete_objects(deduped)
        except Exception as exc:
            logger.warning("S3 delete_objects failed (continuing): %s", exc)

    def _invalidate_cf_paths(self, keys_or_paths: List[str]) -> None:
        if self._cf_invalidator is None:
            return
        try:
            self._cf_invalidator.invalidate_paths(keys_or_paths)
        except Exception as exc:
            logger.warning("CloudFront invalidation failed (continuing): %s", exc)

    def _safe_presign_get(self, key: str, *, media: str) -> str | None:
        """Presign GET for display URLs, or None if the key cannot be signed.

        One bad or legacy S3 key must not fail entire list endpoints (for example
        ``GET /courses/{id}/lessons``) for every lesson in the course.
        """
        if self._storage is None:
            return None
        k = (key or "").strip()
        if not k:
            return None
        try:
            if self._cloudfront_signer is not None:
                return self._storage.presign_get_cloudfront(
                    key=k,
                    expires_seconds=self._media_get_expires_seconds,
                    signer=self._cloudfront_signer,
                )
            return self._storage.presign_get(
                key=k, expires_seconds=self._media_get_expires_seconds
            )
        except BadRequest:
            logger.warning("presign_get rejected key for %s", media, extra={"key_prefix": k[:96]})
            return None
        except Exception as exc:  # pragma: no cover - botocore / network edge paths
            logger.warning("presign_get failed for %s: %s", media, exc, extra={"key_prefix": k[:96]})
            return None

    def _public_course_dict(self, course: Course) -> Dict[str, Any]:
        data = asdict(course)
        thumb_key = (data.pop("thumbnailKey", None) or "").strip()
        if thumb_key and self._storage is not None:
            url = self._safe_presign_get(thumb_key, media="course_thumbnail")
            if url:
                data["thumbnailUrl"] = url
        return data

    def _apply_course_cover_fallback(self, course_id: str, public: Dict[str, Any]) -> None:
        """When no course cover is set, use the first lesson thumbnail (by order) for catalog/hero."""
        if public.get("thumbnailUrl") or self._storage is None:
            return
        lessons = self._repo.list_lessons(course_id)
        for lesson in sorted(lessons, key=lambda l: l.order):
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
        if thumb_key and self._storage is not None:
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
        auth_enforced: bool,
    ) -> List[Dict[str, Any]]:
        """Courses for the instructor dashboard (draft + published), scoped by owner unless admin."""
        sub = (cognito_sub or "").strip()
        if not auth_enforced:
            courses = self._repo.list_courses()
        elif self._is_admin(role):
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
            return True
        return owner == cognito_sub.strip()

    def viewer_has_lesson_access(
        self,
        course: Course,
        *,
        course_id: str,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> bool:
        if not auth_enforced:
            return True
        if not cognito_sub.strip():
            return False
        if self._can_manage_course_unenrolled(course, cognito_sub=cognito_sub, role=role):
            return True
        if course.status != "PUBLISHED":
            return False
        return self._enrollments.has_enrollment(user_sub=cognito_sub, course_id=course_id)

    def ensure_can_view_lessons_and_playback(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> Course:
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if not auth_enforced:
            return course
        if not cognito_sub.strip():
            raise Forbidden("Authentication required", code="forbidden")
        if self.viewer_has_lesson_access(
            course, course_id=course_id, cognito_sub=cognito_sub, role=role, auth_enforced=auth_enforced
        ):
            return course
        raise Forbidden("Enrollment required to view this course", code="enrollment_required")

    def get_course_preview(self, course_id: str) -> Dict[str, Any]:
        course = self._repo.get_course(course_id)
        if not course or course.status != "PUBLISHED":
            raise NotFound("Course not found")
        data = self._public_course_dict(course)
        self._apply_course_cover_fallback(course_id, data)
        lessons = self._repo.list_lessons(course_id)
        preview_lessons = [
            {"id": l.id, "title": l.title, "order": l.order}
            for l in sorted(lessons, key=lambda x: x.order)
        ]
        data["lessonsPreview"] = preview_lessons
        return data

    def get_course_detail_with_enrollment(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> Dict[str, Any]:
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if auth_enforced:
            if course.status == "DRAFT":
                if not self._can_manage_course_unenrolled(course, cognito_sub=cognito_sub, role=role):
                    raise NotFound("Course not found")
            has_lessons = self.viewer_has_lesson_access(
                course, course_id=course_id, cognito_sub=cognito_sub, role=role, auth_enforced=auth_enforced
            )
        else:
            has_lessons = True
        data = self._public_course_dict(course)
        self._apply_course_cover_fallback(course_id, data)
        data["enrolled"] = bool(has_lessons)
        return data

    def enroll_in_published_course(self, course_id: str, *, cognito_sub: str) -> Dict[str, Any]:
        if not cognito_sub.strip():
            raise Forbidden("Authentication required", code="forbidden")
        course = self._repo.get_course(course_id)
        if not course or course.status != "PUBLISHED":
            raise NotFound("Course not found")
        self._enrollments.put_enrollment(user_sub=cognito_sub, course_id=course_id)
        return {"courseId": course_id, "enrolled": True}

    def create_course(self, title: str, description: str, *, created_by: str = "") -> Dict[str, Any]:
        course = self._repo.create_course(
            title=title or "Untitled Course",
            description=description or "",
            created_by=created_by or "",
        )
        return {"id": course.id, "status": course.status}

    def ensure_can_modify_course(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> None:
        """When auth is enforced, only teacher/admin may mutate; admin bypasses ownership."""
        if not auth_enforced:
            return
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
            return
        if owner != cognito_sub:
            raise Forbidden("Not allowed to modify this course")

    def update_course(self, course_id: str, title: str, description: str) -> Dict[str, Any]:
        self._repo.update_course(course_id=course_id, title=title, description=description)
        return {"id": course_id, "updated": True}

    def delete_course(self, course_id: str) -> Dict[str, Any]:
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
        # Remove DB rows first so catalog reflects the delete even if S3 is slow.
        self._repo.delete_course_and_lessons(course_id)
        self._delete_media_keys(keys)
        self._invalidate_cf_paths(keys)
        return {"id": course_id, "deleted": True}

    def list_lessons(self, course_id: str) -> List[Dict[str, Any]]:
        return [self._public_lesson_dict(l) for l in self._repo.list_lessons(course_id)]

    def create_lesson(self, course_id: str, title: str) -> Dict[str, Any]:
        lesson = self._repo.create_lesson(course_id=course_id, title=title or "Lesson")
        return {"lessonId": lesson.id, "order": lesson.order}

    def update_lesson(self, course_id: str, lesson_id: str, title: str) -> Dict[str, Any]:
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        self._repo.update_lesson_title(course_id=course_id, lesson_id=lesson_id, title=title or lesson.title)
        return {"lessonId": lesson_id, "updated": True}

    def delete_lesson(self, course_id: str, lesson_id: str) -> Dict[str, Any]:
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        media_keys: List[str] = []
        if lesson.videoKey.strip():
            media_keys.append(lesson.videoKey.strip())
        if lesson.thumbnailKey.strip():
            media_keys.append(lesson.thumbnailKey.strip())
        self._delete_media_keys(media_keys)
        self._invalidate_cf_paths(media_keys)
        self._repo.delete_lesson(course_id=course_id, lesson_id=lesson_id)
        # Compact remaining orders to 1..N so display has no gaps.
        remaining = sorted(self._repo.list_lessons(course_id), key=lambda l: l.order)
        mapping = {l.id: i + 1 for i, l in enumerate(remaining) if l.id}
        if mapping:
            self._repo.set_lesson_orders(course_id, mapping)
        return {"lessonId": lesson_id, "deleted": True}

    def publish_course(self, course_id: str) -> Dict[str, Any]:
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
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        if not lesson.videoKey:
            raise BadRequest("No video uploaded for lesson")
        old_thumb = lesson.thumbnailKey.strip()
        if thumbnail_key:
            self._validate_lesson_thumbnail_key(course_id, lesson_id, thumbnail_key)
            if old_thumb and old_thumb != thumbnail_key.strip():
                self._delete_media_keys([old_thumb])
            self._repo.set_lesson_thumbnail(course_id, lesson_id, thumbnail_key)
        self._repo.set_lesson_video_status(course_id=course_id, lesson_id=lesson_id, status="ready")
        inv_paths: List[str] = [lesson.videoKey.strip()]
        if thumbnail_key:
            nt = thumbnail_key.strip()
            if old_thumb and old_thumb != nt:
                inv_paths.append(old_thumb)
            inv_paths.append(nt)
        self._invalidate_cf_paths(inv_paths)
        return {"lessonId": lesson_id, "videoStatus": "ready"}

    def get_playback_url(self, course_id: str, lesson_id: str, *, video_bucket: str) -> Dict[str, Any]:
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        if lesson.videoStatus != "ready":
            raise BadRequest("Video not ready")
        if not lesson.videoKey:
            raise NotFound("No video uploaded")
        if self._storage is None:
            return {"url": f"https://{video_bucket}.s3.amazonaws.com/{lesson.videoKey}"}
        if self._cloudfront_signer is not None:
            return {
                "url": self._storage.presign_get_cloudfront(
                    key=lesson.videoKey,
                    expires_seconds=self._media_get_expires_seconds,
                    signer=self._cloudfront_signer,
                )
            }
        return {
            "url": self._storage.presign_get(
                key=lesson.videoKey, expires_seconds=self._media_get_expires_seconds
            )
        }

    def get_upload_url(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
    ) -> Dict[str, Any]:
        if self._storage is None:
            raise BadRequest("Uploads are not configured")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        expected_key = (lesson.videoKey or "").strip()
        presign = self._storage.presign_put(
            course_id=course_id,
            lesson_id=lesson_id,
            filename=filename,
            content_type=content_type,
        )
        try:
            self._repo.set_lesson_video_if_video_key_matches(
                course_id=course_id,
                lesson_id=lesson_id,
                video_key=presign.videoKey,
                status="pending",
                expected_video_key=expected_key,
            )
        except Conflict:
            self._storage.delete_objects([presign.videoKey])
            raise
        # Do not delete `expected_key` here: a second presign can race with a client
        # still uploading to the first URL. Orphan prior objects are acceptable for MVP;
        # cleanup can be lifecycle or a later sweeper keyed off DB.
        return {"uploadUrl": presign.uploadUrl, "videoKey": presign.videoKey}

    def get_thumbnail_upload_url(
        self,
        *,
        course_id: str,
        filename: str,
        content_type: str,
    ) -> Dict[str, Any]:
        if self._storage is None:
            raise BadRequest("Uploads are not configured")
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        # Do not delete the existing S3 object here: the DB still points at it until
        # mark_course_thumbnail_ready runs. Deleting early breaks thumbnails if the
        # PUT fails or the client never calls thumbnail-ready.
        presign = self._storage.presign_thumbnail_put(
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
        if self._storage is None:
            raise BadRequest("Uploads are not configured")
        lesson = self._repo.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")
        # Same as course thumbnails: keep the old object until mark_lesson_video_ready
        # persists the new key (that path deletes the previous key from S3).
        presign = self._storage.presign_lesson_thumbnail_put(
            course_id=course_id,
            lesson_id=lesson_id,
            filename=filename,
            content_type=content_type,
        )
        return {"uploadUrl": presign.uploadUrl, "thumbnailKey": presign.videoKey}

    def mark_course_thumbnail_ready(self, course_id: str, thumbnail_key: str) -> Dict[str, Any]:
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        self._validate_thumbnail_key(course_id, thumbnail_key)
        old_thumb = course.thumbnailKey.strip()
        if old_thumb and old_thumb != thumbnail_key.strip():
            self._delete_media_keys([old_thumb])
        self._repo.set_course_thumbnail(course_id, thumbnail_key)
        inv_paths = [thumbnail_key.strip()]
        if old_thumb and old_thumb != thumbnail_key.strip():
            inv_paths.append(old_thumb)
        self._invalidate_cf_paths(inv_paths)
        return {"id": course_id, "thumbnailReady": True}

