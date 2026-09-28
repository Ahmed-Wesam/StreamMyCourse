from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Sequence

from services.course_management.models import Course, CourseModule, Lesson, LessonFile, PresignResult


class UserProfileProvisioner(Protocol):
    """Minimal surface from ``UserProfileService`` used by course HTTP handlers."""

    def get_or_create_profile(self, *, user_sub: str, email: str, role: str) -> Dict[str, Any]: ...


class CourseCatalogRepositoryPort(Protocol):
    def list_courses(self) -> List[Course]: ...
    def list_courses_by_instructor(self, created_by: str) -> List[Course]: ...
    def get_course(self, course_id: str) -> Optional[Course]: ...
    def create_course(self, title: str, description: str, *, created_by: str) -> Course: ...
    def update_course(
        self,
        course_id: str,
        title: str,
        description: str,
        *,
        page_content: Dict[str, Any] | None = None,
    ) -> None: ...
    def set_course_status(self, course_id: str, status: str) -> None: ...

    def list_course_modules(self, course_id: str) -> List[CourseModule]: ...
    def get_course_module(self, course_id: str, module_id: str) -> Optional[CourseModule]: ...
    def create_course_module(self, course_id: str, title: str, description: str = "") -> CourseModule: ...
    def delete_course_module(self, course_id: str, module_id: str) -> None: ...

    def list_lessons(self, course_id: str) -> List[Lesson]: ...
    def get_lesson_by_id(self, course_id: str, lesson_id: str) -> Optional[Lesson]: ...
    def create_lesson(self, course_id: str, module_id: str, title: str) -> Lesson: ...
    def update_lesson_title(self, course_id: str, lesson_id: str, title: str) -> None: ...
    def delete_lesson(self, course_id: str, lesson_id: str) -> None: ...
    def delete_course_and_lessons(self, course_id: str) -> None: ...
    def set_lesson_video(self, course_id: str, lesson_id: str, video_key: str, status: str) -> None: ...
    def set_lesson_video_if_video_key_matches(
        self, course_id: str, lesson_id: str, video_key: str, status: str, *, expected_video_key: str
    ) -> None: ...
    def set_lesson_video_status(self, course_id: str, lesson_id: str, status: str) -> None: ...
    def set_lesson_orders(self, course_id: str, orders: Dict[str, int]) -> None: ...
    def set_course_thumbnail(self, course_id: str, thumbnail_key: str) -> None: ...
    def set_lesson_thumbnail(self, course_id: str, lesson_id: str, thumbnail_key: str) -> None: ...
    def set_lesson_duration(self, course_id: str, lesson_id: str, duration: int) -> None: ...
    def find_lesson_by_video_key(self, video_key: str) -> Optional[tuple[str, str]]: ...

    def count_lesson_files(self, course_id: str, lesson_id: str) -> int: ...
    def create_lesson_file(
        self,
        *,
        file_id: str,
        course_id: str,
        lesson_id: str,
        kind: str,
        title: str,
        object_key: str,
        content_type: str,
        byte_size: int,
    ) -> LessonFile: ...
    def get_lesson_file(
        self, course_id: str, lesson_id: str, file_id: str
    ) -> Optional[LessonFile]: ...
    def list_lesson_files(
        self, course_id: str, lesson_id: str, *, ready_only: bool
    ) -> List[LessonFile]: ...
    def mark_lesson_file_ready(self, course_id: str, lesson_id: str, file_id: str) -> None: ...
    def delete_lesson_file(self, course_id: str, lesson_id: str, file_id: str) -> None: ...
    def list_lesson_file_object_keys_for_lesson(
        self, course_id: str, lesson_id: str
    ) -> List[str]: ...
    def list_lesson_file_object_keys_for_lessons(
        self, course_id: str, lesson_ids: Sequence[str]
    ) -> List[str]: ...
    def list_lesson_file_object_keys_for_course(self, course_id: str) -> List[str]: ...


class StudentModuleLockPort(Protocol):
    """Whether a module is quiz-gated locked for a student (owner/admin bypass in adapter)."""

    def is_module_locked_for_student(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> bool: ...


class ModuleQuizVisibilityPort(Protocol):
    def module_quiz_visibility_by_course(
        self,
        course_id: str,
        *,
        course_status: str,
        has_lesson_access: bool,
        cognito_sub: str,
    ) -> Dict[str, Dict[str, Any]]: ...


class ImageMediaStoragePort(Protocol):
    def presign_thumbnail_put(
        self,
        *,
        course_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> PresignResult: ...
    def presign_lesson_thumbnail_put(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> PresignResult: ...
    def presign_get(self, *, key: str, expires_seconds: int = 3600) -> str: ...
    def delete_object(self, key: str) -> None: ...
    def delete_objects(self, keys: Sequence[str]) -> List[str]: ...


class LessonFileStoragePort(Protocol):
    def presign_put_file(
        self,
        *,
        course_id: str,
        lesson_id: str,
        file_id: str,
        file_type: str,
        byte_size: int,
        expires_seconds: int = 300,
    ) -> Any: ...

    def head_object(self, key: str) -> dict: ...

    def delete_object(self, key: str) -> None: ...

    def presign_get_file(
        self,
        *,
        key: str,
        kind: str,
        title: str,
        file_type: str,
        expires_seconds: int = 300,
    ) -> str: ...


# Deprecated alias — remove after downstream imports migrate.
CourseMediaStoragePort = ImageMediaStoragePort

