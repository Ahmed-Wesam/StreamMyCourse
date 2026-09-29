"""Assignment domain service (RS-13): publish, submit, grade, access rules."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence
from uuid import UUID, uuid4

from services.assignments.contracts import (
    AssignmentItem,
    ContentBlock,
    CriterionItem,
    GradeResponse,
    ListAssignmentsResponse,
    ListSubmissionsResponse,
    MyLatestItem,
    SubmissionItem,
)
from services.assignments.models import (
    DEFAULT_PASS_PERCENT,
    MAX_ASSIGNMENTS_PER_COURSE,
    MAX_CRITERIA_PER_ASSIGNMENT,
    MAX_FILES_PER_SUBMISSION,
    PRESIGN_GET_TTL_SECONDS,
)
from services.assignments.ports import (
    AssignmentMailPort,
    AssignmentRow,
    AssignmentsRepositoryPort,
    AssignmentStoragePort,
    CertificateIssuerPort,
    CourseAccessPort,
    CourseLookupPort,
    CourseOwnerInfo,
    CriterionRow,
    MediaCleanupPort,
    NotifyMailMessage,
    QuizLockPort,
    SubmissionRow,
    UserEmailPort,
)
from services.assignments.validation import (
    content_type_for_file_type,
    extension_for_image_content_type,
    reject_unknown_keys,
    sanitize_download_filename,
    sanitize_rich_html,
    score_percent_half_up,
    validate_bool,
    validate_criterion_label,
    validate_criterion_max_points,
    validate_feedback,
    validate_image_upload,
    validate_note,
    validate_pass_percent,
    validate_plain_text,
    validate_submission_byte_size,
    validate_submission_file_type,
    validate_title,
)
from services.common.errors import (
    BadRequest,
    Conflict,
    Forbidden,
    NotFound,
    ServiceUnavailable,
)

logger = logging.getLogger(__name__)


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
    except Exception:
        return False
    return True


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AssignmentsService:
    def __init__(
        self,
        repo: AssignmentsRepositoryPort,
        storage: AssignmentStoragePort,
        course_access: CourseAccessPort,
        quiz_lock: QuizLockPort,
        course_lookup: CourseLookupPort,
        cleanup: MediaCleanupPort,
        mail: AssignmentMailPort,
        user_email: UserEmailPort,
        certificate_issuer: CertificateIssuerPort | None = None,
    ) -> None:
        self._repo = repo
        self._storage = storage
        self._course_access = course_access
        self._quiz_lock = quiz_lock
        self._course_lookup = course_lookup
        self._cleanup = cleanup
        self._mail = mail
        self._user_email = user_email
        self._certificate_issuer = certificate_issuer

    # --- authorization helpers -------------------------------------------------

    def _get_course(self, course_id: str) -> CourseOwnerInfo:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._course_lookup.get_course(course_id)
        if course is None:
            raise NotFound("Course not found")
        return course

    def _can_modify_course(self, course: CourseOwnerInfo, *, cognito_sub: str, role: str) -> bool:
        sub = (cognito_sub or "").strip()
        r = (role or "").strip().lower()
        if not sub:
            return False
        if r == "admin":
            return True
        if r != "teacher":
            return False
        owner = (course.created_by or "").strip()
        return bool(owner) and owner == sub

    def _ensure_can_modify(self, course_id: str, *, cognito_sub: str, role: str) -> CourseOwnerInfo:
        course = self._get_course(course_id)
        r = (role or "").strip().lower()
        if r == "admin":
            return course
        if r not in ("teacher", "admin"):
            raise Forbidden("Teacher or admin role required")
        owner = (course.created_by or "").strip()
        if not owner:
            raise BadRequest("Course has no owner (created_by is blank)")
        if owner != (cognito_sub or "").strip():
            raise Forbidden("Not allowed to modify this course")
        return course

    def _ensure_student_access(
        self,
        *,
        course_id: str,
        module_id: str,
        cognito_sub: str,
        role: str,
        course: CourseOwnerInfo | None = None,
    ) -> None:
        """Purchase + module lock, unless caller can modify the course."""
        info = course or self._get_course(course_id)
        if self._can_modify_course(info, cognito_sub=cognito_sub, role=role):
            return
        if not self._course_access.has_course_access(cognito_sub, course_id, role):
            raise Forbidden(
                "Purchase required to access assignments",
                code="purchase_required",
            )
        if self._quiz_lock.is_module_locked_for_student(
            course_id,
            module_id,
            cognito_sub=cognito_sub,
            role=role,
        ):
            raise Forbidden(
                "Complete the prior module quiz to unlock this content",
                code="module_locked",
            )

    def _get_assignment_or_404(self, course_id: str, assignment_id: str) -> AssignmentRow:
        if not _is_valid_uuid(assignment_id):
            raise NotFound("Assignment not found")
        row = self._repo.get_assignment(course_id, assignment_id)
        if row is None:
            raise NotFound("Assignment not found")
        return row

    # --- serialization ---------------------------------------------------------

    def _content_block(self, *, mode: str, text: str, html: str, image_ready: bool) -> ContentBlock:
        block: ContentBlock = {"mode": mode}
        if mode == "plain":
            block["text"] = text
        elif mode == "rich":
            block["html"] = html
        elif mode == "image":
            block["imageReady"] = image_ready
        return block

    def _criteria_items(self, criteria: Sequence[CriterionRow]) -> List[CriterionItem]:
        return [
            {"id": c.id, "label": c.label, "maxPoints": c.max_points}
            for c in criteria
        ]

    def _my_latest(self, submission: SubmissionRow | None) -> MyLatestItem | None:
        if submission is None:
            return None
        item: MyLatestItem = {"id": submission.id, "status": submission.status}
        if submission.grade is not None:
            item["scorePercent"] = submission.grade.score_percent
            item["passed"] = submission.grade.passed
            item["feedback"] = submission.grade.feedback
        return item

    def _to_assignment_item(
        self,
        row: AssignmentRow,
        *,
        locked: bool,
        my_latest: SubmissionRow | None,
    ) -> AssignmentItem:
        return {
            "id": row.id,
            "title": row.title,
            "moduleId": row.module_id,
            "status": row.status,
            "passPercent": row.pass_percent,
            "countsTowardCertificate": row.counts_toward_certificate,
            "locked": locked,
            "instructions": self._content_block(
                mode=row.instructions_mode,
                text=row.instructions_text,
                html=row.instructions_html,
                image_ready=row.instructions_image_ready,
            ),
            "rubric": self._content_block(
                mode=row.rubric_mode,
                text=row.rubric_text,
                html=row.rubric_html,
                image_ready=row.rubric_image_ready,
            ),
            "criteria": self._criteria_items(row.criteria),
            "myLatest": self._my_latest(my_latest),
        }

    def _to_submission_item(
        self, row: SubmissionRow, *, include_user_sub: bool
    ) -> SubmissionItem:
        item: SubmissionItem = {
            "id": row.id,
            "status": row.status,
            "note": row.note,
            "files": [
                {
                    "id": f.id,
                    "title": f.title,
                    "fileType": f.file_type,
                    "byteSize": f.byte_size,
                    "status": f.status,
                }
                for f in row.files
            ],
        }
        if include_user_sub:
            item["userSub"] = row.user_sub
        if row.grade is not None:
            item["grade"] = {
                "scorePercent": row.grade.score_percent,
                "passed": row.grade.passed,
                "feedback": row.grade.feedback,
                "scores": [
                    {"criterionId": s.criterion_id, "points": s.points}
                    for s in row.grade.scores
                ],
            }
        return item

    def _is_locked_for_viewer(
        self,
        *,
        course_id: str,
        module_id: str,
        cognito_sub: str,
        role: str,
        course: CourseOwnerInfo,
    ) -> bool:
        if self._can_modify_course(course, cognito_sub=cognito_sub, role=role):
            return False
        if not self._course_access.has_course_access(cognito_sub, course_id, role):
            return True
        return self._quiz_lock.is_module_locked_for_student(
            course_id,
            module_id,
            cognito_sub=cognito_sub,
            role=role,
        )

    # --- publish helpers -------------------------------------------------------

    def _has_instructions_body(self, row: AssignmentRow) -> bool:
        if row.instructions_mode == "plain":
            return bool(row.instructions_text.strip())
        if row.instructions_mode == "rich":
            return bool(row.instructions_html.strip())
        if row.instructions_mode == "image":
            return bool(row.instructions_image_key) and row.instructions_image_ready
        return False

    def _assert_publishable(self, row: AssignmentRow) -> None:
        if not self._has_instructions_body(row):
            raise BadRequest(
                "Instructions are required to publish",
                code="instructions_required",
            )
        if not row.criteria:
            raise BadRequest(
                "At least one criterion is required to publish",
                code="criteria_required",
            )
        if len(row.criteria) > MAX_CRITERIA_PER_ASSIGNMENT:
            raise BadRequest(
                f"At most {MAX_CRITERIA_PER_ASSIGNMENT} criteria are allowed",
                code="criteria_limit",
            )
        total = sum(c.max_points for c in row.criteria)
        if total <= 0:
            raise BadRequest(
                "Sum of criterion maxPoints must be greater than 0",
                code="criteria_required",
            )

    # --- teacher mutations -----------------------------------------------------

    def create_assignment(
        self,
        course_id: str,
        *,
        title: str,
        module_id: str,
        pass_percent: int | None = None,
        counts_toward_certificate: bool | None = None,
        cognito_sub: str,
        role: str,
        body: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if body is not None:
            reject_unknown_keys(
                body,
                {
                    "title",
                    "moduleId",
                    "passPercent",
                    "countsTowardCertificate",
                },
            )
        self._ensure_can_modify(course_id, cognito_sub=cognito_sub, role=role)
        if not _is_valid_uuid(module_id):
            raise BadRequest("moduleId must be a UUID", code="invalid_module")
        if not self._course_lookup.module_belongs_to_course(course_id, module_id):
            raise BadRequest("moduleId does not belong to this course", code="invalid_module")
        clean_title = validate_title(title)
        pp = validate_pass_percent(pass_percent, default=DEFAULT_PASS_PERCENT)
        flag = validate_bool(
            counts_toward_certificate,
            field="countsTowardCertificate",
            default=False,
        )
        if self._repo.count_assignments_for_course(course_id) >= MAX_ASSIGNMENTS_PER_COURSE:
            raise Conflict(
                f"Maximum of {MAX_ASSIGNMENTS_PER_COURSE} assignments per course",
                code="assignment_limit",
            )
        row = self._repo.insert_assignment(
            course_id=course_id,
            module_id=module_id,
            title=clean_title,
            pass_percent=pp,
            counts_toward_certificate=flag,
            status="draft",
        )
        return {
            "assignment": self._to_assignment_item(row, locked=False, my_latest=None)
        }

    def update_assignment(
        self,
        course_id: str,
        assignment_id: str,
        *,
        cognito_sub: str,
        role: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        reject_unknown_keys(
            body,
            {
                "title",
                "moduleId",
                "passPercent",
                "countsTowardCertificate",
                "status",
                "instructions",
                "rubric",
                "criteria",
            },
        )
        self._ensure_can_modify(course_id, cognito_sub=cognito_sub, role=role)
        row = self._get_assignment_or_404(course_id, assignment_id)

        title = row.title
        if "title" in body:
            title = validate_title(body["title"])

        module_id = row.module_id
        if "moduleId" in body:
            mid = body["moduleId"]
            if not isinstance(mid, str) or not _is_valid_uuid(mid):
                raise BadRequest("moduleId must be a UUID", code="invalid_module")
            if not self._course_lookup.module_belongs_to_course(course_id, mid):
                raise BadRequest(
                    "moduleId does not belong to this course", code="invalid_module"
                )
            module_id = mid

        pass_percent = row.pass_percent
        if "passPercent" in body:
            pass_percent = validate_pass_percent(body["passPercent"])

        flag = row.counts_toward_certificate
        if "countsTowardCertificate" in body:
            flag = validate_bool(
                body["countsTowardCertificate"], field="countsTowardCertificate"
            )

        instructions_mode = row.instructions_mode
        instructions_text = row.instructions_text
        instructions_html = row.instructions_html
        instructions_image_key = row.instructions_image_key
        instructions_image_ready = row.instructions_image_ready
        old_keys: list[str] = []

        if "instructions" in body:
            (
                instructions_mode,
                instructions_text,
                instructions_html,
                instructions_image_key,
                instructions_image_ready,
                dropped,
            ) = self._apply_content_update(
                body["instructions"],
                field="instructions",
                current_mode=row.instructions_mode,
                current_image_key=row.instructions_image_key,
                current_image_ready=row.instructions_image_ready,
            )
            old_keys.extend(dropped)

        rubric_mode = row.rubric_mode
        rubric_text = row.rubric_text
        rubric_html = row.rubric_html
        rubric_image_key = row.rubric_image_key
        rubric_image_ready = row.rubric_image_ready
        if "rubric" in body:
            (
                rubric_mode,
                rubric_text,
                rubric_html,
                rubric_image_key,
                rubric_image_ready,
                dropped,
            ) = self._apply_content_update(
                body["rubric"],
                field="rubric",
                current_mode=row.rubric_mode,
                current_image_key=row.rubric_image_key,
                current_image_ready=row.rubric_image_ready,
            )
            old_keys.extend(dropped)

        criteria = list(row.criteria)
        if "criteria" in body:
            criteria = self._replace_criteria_from_body(assignment_id, body["criteria"])

        status = row.status
        if "status" in body:
            new_status = body["status"]
            if new_status not in ("draft", "published"):
                raise BadRequest("status must be draft or published")
            status = new_status

        updated = replace(
            row,
            module_id=module_id,
            title=title,
            status=status,
            pass_percent=pass_percent,
            counts_toward_certificate=flag,
            instructions_mode=instructions_mode,
            instructions_text=instructions_text,
            instructions_html=instructions_html,
            instructions_image_key=instructions_image_key,
            instructions_image_ready=instructions_image_ready,
            rubric_mode=rubric_mode,
            rubric_text=rubric_text,
            rubric_html=rubric_html,
            rubric_image_key=rubric_image_key,
            rubric_image_ready=rubric_image_ready,
            updated_at=_now(),
            criteria=tuple(criteria),
        )

        if status == "published":
            self._assert_publishable(updated)

        saved = self._repo.update_assignment(updated)
        if old_keys:
            self._enqueue_cleanup(old_keys)
        return {
            "assignment": self._to_assignment_item(saved, locked=False, my_latest=None)
        }

    def _apply_content_update(
        self,
        raw: Any,
        *,
        field: str,
        current_mode: str,
        current_image_key: str,
        current_image_ready: bool,
    ) -> tuple[str, str, str, str, bool, list[str]]:
        if not isinstance(raw, dict):
            raise BadRequest(f"{field} must be an object")
        reject_unknown_keys(raw, {"mode", "text", "html"})
        mode = raw.get("mode")
        if mode not in ("plain", "rich", "image"):
            raise BadRequest(f"{field}.mode must be plain, rich, or image")
        dropped: list[str] = []
        text = ""
        html_out = ""
        image_key = current_image_key
        image_ready = current_image_ready
        if mode == "plain":
            text = validate_plain_text(raw.get("text", ""), field=f"{field}.text")
            if current_mode == "image" and current_image_key:
                dropped.append(current_image_key)
            image_key = ""
            image_ready = False
        elif mode == "rich":
            html_out = sanitize_rich_html(raw.get("html", ""))
            if current_mode == "image" and current_image_key:
                dropped.append(current_image_key)
            image_key = ""
            image_ready = False
        else:
            # mode image: keep existing key/ready unless none yet
            text = ""
            html_out = ""
            if current_mode != "image":
                image_key = ""
                image_ready = False
        return mode, text, html_out, image_key, image_ready, dropped

    def _replace_criteria_from_body(
        self, assignment_id: str, raw: Any
    ) -> List[CriterionRow]:
        if not isinstance(raw, list):
            raise BadRequest("criteria must be an array")
        if len(raw) > MAX_CRITERIA_PER_ASSIGNMENT:
            raise BadRequest(
                f"At most {MAX_CRITERIA_PER_ASSIGNMENT} criteria are allowed",
                code="criteria_limit",
            )
        prepared: list[tuple[str, str, int]] = []
        for item in raw:
            if not isinstance(item, dict):
                raise BadRequest("each criterion must be an object")
            reject_unknown_keys(item, {"id", "label", "maxPoints"})
            label = validate_criterion_label(item.get("label"))
            max_points = validate_criterion_max_points(item.get("maxPoints"))
            cid = item.get("id")
            if cid is None:
                cid = str(uuid4())
            elif not isinstance(cid, str) or not _is_valid_uuid(cid):
                raise BadRequest("criterion id must be a UUID")
            prepared.append((cid, label, max_points))
        return self._repo.replace_criteria(assignment_id=assignment_id, criteria=prepared)

    def publish_assignment(
        self,
        course_id: str,
        assignment_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        return self.update_assignment(
            course_id,
            assignment_id,
            cognito_sub=cognito_sub,
            role=role,
            body={"status": "published"},
        )

    def delete_assignment(
        self,
        course_id: str,
        assignment_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        self._ensure_can_modify(course_id, cognito_sub=cognito_sub, role=role)
        self._get_assignment_or_404(course_id, assignment_id)
        keys = [
            k
            for k in self._repo.list_object_keys_for_assignment(course_id, assignment_id)
            if k
        ]
        if keys and not (self._cleanup.queue_url() or "").strip():
            raise ServiceUnavailable(
                "Media cleanup queue is not configured (MEDIA_CLEANUP_QUEUE_URL is empty)"
            )
        deleted = self._repo.delete_assignment(course_id, assignment_id)
        if not deleted:
            raise NotFound("Assignment not found")
        if keys:
            self._enqueue_cleanup(keys)
        return {"ok": True}

    def _enqueue_cleanup(self, keys: Sequence[str]) -> None:
        cleaned = [k for k in keys if k]
        if not cleaned:
            return
        if not (self._cleanup.queue_url() or "").strip():
            raise ServiceUnavailable(
                "Media cleanup queue is not configured (MEDIA_CLEANUP_QUEUE_URL is empty)"
            )
        self._cleanup.enqueue_object_keys(cleaned)

    # --- list / get ------------------------------------------------------------

    def list_assignments(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> ListAssignmentsResponse:
        course = self._get_course(course_id)
        can_modify = self._can_modify_course(course, cognito_sub=cognito_sub, role=role)
        if not can_modify:
            if not self._course_access.has_course_access(cognito_sub, course_id, role):
                raise Forbidden(
                    "Purchase required to access assignments",
                    code="purchase_required",
                )
        rows = self._repo.list_assignments(course_id, published_only=not can_modify)
        items: list[AssignmentItem] = []
        for row in rows:
            locked = self._is_locked_for_viewer(
                course_id=course_id,
                module_id=row.module_id,
                cognito_sub=cognito_sub,
                role=role,
                course=course,
            )
            latest = None
            if not can_modify:
                latest = self._repo.get_latest_submission_for_user(
                    assignment_id=row.id, user_sub=cognito_sub
                )
            items.append(
                self._to_assignment_item(row, locked=locked, my_latest=latest)
            )
        return {"assignments": items}

    def get_assignment(
        self,
        course_id: str,
        assignment_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        course = self._get_course(course_id)
        can_modify = self._can_modify_course(course, cognito_sub=cognito_sub, role=role)
        row = self._get_assignment_or_404(course_id, assignment_id)
        if not can_modify:
            if row.status != "published":
                raise NotFound("Assignment not found")
            self._ensure_student_access(
                course_id=course_id,
                module_id=row.module_id,
                cognito_sub=cognito_sub,
                role=role,
                course=course,
            )
        locked = self._is_locked_for_viewer(
            course_id=course_id,
            module_id=row.module_id,
            cognito_sub=cognito_sub,
            role=role,
            course=course,
        )
        latest = self._repo.get_latest_submission_for_user(
            assignment_id=row.id, user_sub=cognito_sub
        )
        return {
            "assignment": self._to_assignment_item(
                row, locked=locked, my_latest=latest
            )
        }

    # --- images ----------------------------------------------------------------

    def create_image_upload(
        self,
        course_id: str,
        assignment_id: str,
        *,
        slot: str,
        content_type: str,
        byte_size: int,
        cognito_sub: str,
        role: str,
        body: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if body is not None:
            reject_unknown_keys(body, {"slot", "contentType", "byteSize"})
        self._ensure_can_modify(course_id, cognito_sub=cognito_sub, role=role)
        row = self._get_assignment_or_404(course_id, assignment_id)
        slot_n, ct, size = validate_image_upload(
            slot=slot, content_type=content_type, byte_size=byte_size
        )
        ext = extension_for_image_content_type(ct)
        key = f"{course_id}/assignments/{assignment_id}/images/{slot_n}.{ext}"
        old_key = (
            row.instructions_image_key
            if slot_n == "instructions"
            else row.rubric_image_key
        )
        url = self._storage.presign_put(key, ct, size)
        if slot_n == "instructions":
            updated = replace(
                row,
                instructions_mode="image",
                instructions_text="",
                instructions_html="",
                instructions_image_key=key,
                instructions_image_ready=False,
                updated_at=_now(),
            )
        else:
            updated = replace(
                row,
                rubric_mode="image",
                rubric_text="",
                rubric_html="",
                rubric_image_key=key,
                rubric_image_ready=False,
                updated_at=_now(),
            )
        self._repo.update_assignment(updated)
        if old_key and old_key != key:
            self._enqueue_cleanup([old_key])
        return {"uploadUrl": url}

    def complete_image_upload(
        self,
        course_id: str,
        assignment_id: str,
        slot: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        self._ensure_can_modify(course_id, cognito_sub=cognito_sub, role=role)
        if slot not in ("instructions", "rubric"):
            raise BadRequest("slot must be 'instructions' or 'rubric'")
        row = self._get_assignment_or_404(course_id, assignment_id)
        key = (
            row.instructions_image_key
            if slot == "instructions"
            else row.rubric_image_key
        )
        if not key:
            raise BadRequest("No pending image upload for this slot")
        head = self._storage.head(key)
        if head is None:
            self._storage.delete(key)
            raise BadRequest("Uploaded object not found", code="upload_incomplete")
        # Accept any allowlisted image type; key extension is authoritative for path.
        if head.content_length < 1:
            self._storage.delete(key)
            raise BadRequest("Uploaded object is empty", code="upload_mismatch")
        if slot == "instructions":
            updated = replace(
                row,
                instructions_image_ready=True,
                instructions_mode="image",
                updated_at=_now(),
            )
        else:
            updated = replace(
                row,
                rubric_image_ready=True,
                rubric_mode="image",
                updated_at=_now(),
            )
        saved = self._repo.update_assignment(updated)
        return {
            "assignment": self._to_assignment_item(saved, locked=False, my_latest=None)
        }

    def get_image_url(
        self,
        course_id: str,
        assignment_id: str,
        slot: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        if slot not in ("instructions", "rubric"):
            raise BadRequest("slot must be 'instructions' or 'rubric'")
        course = self._get_course(course_id)
        can_modify = self._can_modify_course(course, cognito_sub=cognito_sub, role=role)
        row = self._get_assignment_or_404(course_id, assignment_id)
        if not can_modify:
            if row.status != "published":
                raise NotFound("Assignment not found")
            self._ensure_student_access(
                course_id=course_id,
                module_id=row.module_id,
                cognito_sub=cognito_sub,
                role=role,
                course=course,
            )
        key = (
            row.instructions_image_key
            if slot == "instructions"
            else row.rubric_image_key
        )
        ready = (
            row.instructions_image_ready
            if slot == "instructions"
            else row.rubric_image_ready
        )
        if not key or not ready:
            raise NotFound("Image not found")
        url = self._storage.presign_get(
            key,
            disposition="inline",
            download_filename=f"{slot}.img",
            expires_seconds=PRESIGN_GET_TTL_SECONDS,
        )
        return {"url": url}

    # --- submissions -----------------------------------------------------------

    def open_draft_submission(
        self,
        course_id: str,
        assignment_id: str,
        *,
        cognito_sub: str,
        role: str,
        body: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if body is not None:
            reject_unknown_keys(body, set())
        course = self._get_course(course_id)
        row = self._get_assignment_or_404(course_id, assignment_id)
        if row.status != "published" and not self._can_modify_course(
            course, cognito_sub=cognito_sub, role=role
        ):
            raise NotFound("Assignment not found")
        if row.status != "published":
            # Teacher may open for preview only when published for students;
            # drafts are not submittable by students (already 404 above).
            raise BadRequest("Assignment must be published to open a submission")
        self._ensure_student_access(
            course_id=course_id,
            module_id=row.module_id,
            cognito_sub=cognito_sub,
            role=role,
            course=course,
        )
        latest = self._repo.get_latest_submission_for_user(
            assignment_id=assignment_id, user_sub=cognito_sub
        )
        if latest is not None:
            if latest.status == "draft":
                return {
                    "submission": self._to_submission_item(
                        latest, include_user_sub=False
                    )
                }
            if latest.status == "submitted":
                raise Conflict(
                    "Submission is awaiting grade",
                    code="submission_pending",
                )
            if latest.status == "graded" and latest.grade and latest.grade.passed:
                raise Conflict(
                    "Assignment already passed",
                    code="already_passed",
                )
            # graded + failed → new draft
        created = self._repo.insert_submission(
            course_id=course_id,
            assignment_id=assignment_id,
            user_sub=cognito_sub,
            status="draft",
        )
        return {
            "submission": self._to_submission_item(created, include_user_sub=False)
        }

    def create_submission_file(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        *,
        title: str,
        file_type: str,
        byte_size: int,
        cognito_sub: str,
        role: str,
        body: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if body is not None:
            reject_unknown_keys(body, {"title", "fileType", "byteSize"})
        submission = self._require_owned_draft(
            course_id, assignment_id, submission_id, cognito_sub=cognito_sub, role=role
        )
        clean_title = validate_plain_text(
            title, field="title", min_len=1, max_len=255, required=True
        )
        ft = validate_submission_file_type(file_type)
        size = validate_submission_byte_size(byte_size)
        if self._repo.count_files_for_submission(submission.id) >= MAX_FILES_PER_SUBMISSION:
            raise Conflict(
                f"Maximum of {MAX_FILES_PER_SUBMISSION} files per submission",
                code="file_limit",
            )
        file_id = str(uuid4())
        ct = content_type_for_file_type(ft)
        key = (
            f"{course_id}/assignments/{assignment_id}/submissions/"
            f"{submission_id}/{file_id}.{ft}"
        )
        url = self._storage.presign_put(key, ct, size)
        self._repo.insert_submission_file(
            file_id=file_id,
            submission_id=submission.id,
            assignment_id=assignment_id,
            course_id=course_id,
            title=clean_title,
            file_type=ft,
            object_key=key,
            content_type=ct,
            byte_size=size,
            status="pending",
        )
        return {"fileId": file_id, "uploadUrl": url}

    def complete_submission_file(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        file_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        self._require_owned_draft(
            course_id, assignment_id, submission_id, cognito_sub=cognito_sub, role=role
        )
        if not _is_valid_uuid(file_id):
            raise NotFound("File not found")
        frow = self._repo.get_submission_file(submission_id=submission_id, file_id=file_id)
        if frow is None:
            raise NotFound("File not found")
        head = self._storage.head(frow.object_key)
        if head is None:
            self._storage.delete(frow.object_key)
            raise BadRequest("Uploaded object not found", code="upload_incomplete")
        if head.content_type.split(";", 1)[0].strip().lower() != frow.content_type.lower():
            self._storage.delete(frow.object_key)
            raise BadRequest("Uploaded content type mismatch", code="upload_mismatch")
        if head.content_length != frow.byte_size:
            self._storage.delete(frow.object_key)
            raise BadRequest("Uploaded size mismatch", code="upload_mismatch")
        ready = self._repo.mark_submission_file_ready(
            submission_id=submission_id, file_id=file_id
        )
        return {
            "file": {
                "id": ready.id,
                "title": ready.title,
                "fileType": ready.file_type,
                "byteSize": ready.byte_size,
                "status": ready.status,
            }
        }

    def get_submission_file_url(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        file_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        submission = self._require_submission_access(
            course_id, assignment_id, submission_id, cognito_sub=cognito_sub, role=role
        )
        frow = self._repo.get_submission_file(submission_id=submission.id, file_id=file_id)
        if frow is None or frow.status != "ready":
            raise NotFound("File not found")
        filename = sanitize_download_filename(frow.title, extension=frow.file_type)
        url = self._storage.presign_get(
            frow.object_key,
            disposition="attachment",
            download_filename=filename,
            expires_seconds=PRESIGN_GET_TTL_SECONDS,
        )
        return {"url": url}

    def submit_submission(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        *,
        note: str | None = None,
        cognito_sub: str,
        role: str,
        body: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if body is not None:
            reject_unknown_keys(body, {"note"})
        submission = self._require_owned_draft(
            course_id, assignment_id, submission_id, cognito_sub=cognito_sub, role=role
        )
        # Reload with files
        full = self._repo.get_submission(
            course_id=course_id, assignment_id=assignment_id, submission_id=submission_id
        )
        assert full is not None
        ready_files = [f for f in full.files if f.status == "ready"]
        if not ready_files:
            raise BadRequest(
                "At least one ready file is required to submit",
                code="files_required",
            )
        clean_note = validate_note(note if note is not None else (body or {}).get("note"))
        updated = SubmissionRow(
            id=full.id,
            assignment_id=full.assignment_id,
            course_id=full.course_id,
            user_sub=full.user_sub,
            status="submitted",
            note=clean_note,
            created_at=full.created_at,
            updated_at=_now(),
            submitted_at=_now(),
            files=full.files,
            grade=None,
        )
        saved = self._repo.update_submission(updated)
        return {
            "submission": self._to_submission_item(saved, include_user_sub=False)
        }

    def list_submissions(
        self,
        course_id: str,
        assignment_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> ListSubmissionsResponse:
        course = self._get_course(course_id)
        self._get_assignment_or_404(course_id, assignment_id)
        can_modify = self._can_modify_course(course, cognito_sub=cognito_sub, role=role)
        r = (role or "").strip().lower()
        if r in ("teacher", "admin") and not can_modify:
            raise Forbidden("Not allowed to list submissions for this course")
        if can_modify:
            rows = self._repo.list_submissions_for_assignment(
                course_id=course_id, assignment_id=assignment_id
            )
            return {
                "submissions": [
                    self._to_submission_item(s, include_user_sub=True) for s in rows
                ]
            }
        # Student: only own rows; require access
        assignment = self._get_assignment_or_404(course_id, assignment_id)
        if assignment.status != "published":
            raise NotFound("Assignment not found")
        self._ensure_student_access(
            course_id=course_id,
            module_id=assignment.module_id,
            cognito_sub=cognito_sub,
            role=role,
            course=course,
        )
        rows = self._repo.list_submissions_for_user(
            course_id=course_id,
            assignment_id=assignment_id,
            user_sub=cognito_sub,
        )
        return {
            "submissions": [
                self._to_submission_item(s, include_user_sub=False) for s in rows
            ]
        }

    def get_submission(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> Dict[str, Any]:
        submission = self._require_submission_access(
            course_id, assignment_id, submission_id, cognito_sub=cognito_sub, role=role
        )
        course = self._get_course(course_id)
        include = self._can_modify_course(course, cognito_sub=cognito_sub, role=role)
        return {
            "submission": self._to_submission_item(
                submission, include_user_sub=include
            )
        }

    def grade_submission(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        *,
        scores: Sequence[Dict[str, Any]],
        feedback: str,
        cognito_sub: str,
        role: str,
        body: Dict[str, Any] | None = None,
    ) -> GradeResponse:
        if body is not None:
            reject_unknown_keys(body, {"scores", "feedback"})
        course = self._ensure_can_modify(course_id, cognito_sub=cognito_sub, role=role)
        assignment = self._get_assignment_or_404(course_id, assignment_id)
        submission = self._repo.get_submission(
            course_id=course_id,
            assignment_id=assignment_id,
            submission_id=submission_id,
        )
        if submission is None:
            raise NotFound("Submission not found")
        if submission.status == "graded" or submission.grade is not None:
            raise Conflict("Grade is immutable", code="grade_immutable")
        if submission.status != "submitted":
            raise Conflict("Submission is not awaiting grade", code="not_submitted")

        if not isinstance(scores, list):
            raise BadRequest("scores must be an array")
        criteria_by_id = {c.id: c for c in assignment.criteria}
        if len(scores) != len(criteria_by_id):
            raise BadRequest("scores must include exactly one entry per criterion")
        awarded = 0
        max_total = 0
        parsed: list[tuple[str, int]] = []
        seen: set[str] = set()
        for item in scores:
            if not isinstance(item, dict):
                raise BadRequest("each score must be an object")
            reject_unknown_keys(item, {"criterionId", "points"})
            cid = item.get("criterionId")
            if not isinstance(cid, str) or cid not in criteria_by_id:
                raise BadRequest("Unknown criterionId", code="invalid_score")
            if cid in seen:
                raise BadRequest("Duplicate criterionId", code="invalid_score")
            seen.add(cid)
            pts = item.get("points")
            if isinstance(pts, bool) or not isinstance(pts, int):
                raise BadRequest("points must be an integer")
            max_pts = criteria_by_id[cid].max_points
            if pts < 0 or pts > max_pts:
                raise BadRequest(
                    f"points must be between 0 and {max_pts}",
                    code="invalid_score",
                )
            awarded += pts
            max_total += max_pts
            parsed.append((cid, pts))
        if seen != set(criteria_by_id):
            raise BadRequest("scores must include every criterion")

        clean_feedback = validate_feedback(feedback)
        percent = score_percent_half_up(awarded=awarded, max_total=max_total)
        threshold = assignment.pass_percent
        passed = percent >= threshold
        grade = self._repo.insert_grade(
            submission_id=submission_id,
            assignment_id=assignment_id,
            course_id=course_id,
            score_percent=percent,
            pass_percent=threshold,
            passed=passed,
            feedback=clean_feedback,
            graded_by=cognito_sub,
            scores=parsed,
        )
        # Persist submission status
        updated = SubmissionRow(
            id=submission.id,
            assignment_id=submission.assignment_id,
            course_id=submission.course_id,
            user_sub=submission.user_sub,
            status="graded",
            note=submission.note,
            created_at=submission.created_at,
            updated_at=_now(),
            submitted_at=submission.submitted_at,
            files=submission.files,
            grade=grade,
        )
        self._repo.update_submission(updated)

        self._try_notify_grade(
            course=course,
            assignment=assignment,
            student_sub=submission.user_sub,
            score_percent=percent,
            passed=passed,
            feedback=clean_feedback,
            assignment_id=assignment_id,
            submission_id=submission_id,
        )
        if passed and self._certificate_issuer is not None:
            try:
                self._certificate_issuer.try_issue(
                    user_sub=submission.user_sub,
                    course_id=course_id,
                    role="student",
                )
            except Exception:
                logger.exception(
                    "Certificate issue after assignment pass failed",
                    extra={
                        "course_id": course_id,
                        "assignment_id": assignment_id,
                        "submission_id": submission_id,
                        "user_sub": submission.user_sub,
                    },
                )
        return {"scorePercent": percent, "passed": passed}

    def _try_notify_grade(
        self,
        *,
        course: CourseOwnerInfo,
        assignment: AssignmentRow,
        student_sub: str,
        score_percent: int,
        passed: bool,
        feedback: str,
        assignment_id: str,
        submission_id: str,
    ) -> None:
        try:
            to_addr = (self._user_email.get_email_for_user_sub(student_sub) or "").strip()
            if not to_addr:
                logger.info(
                    "Grade notify skipped: empty email",
                    extra={
                        "assignment_id": assignment_id,
                        "submission_id": submission_id,
                    },
                )
                return
            result = "passed" if passed else "failed"
            subject = f"{course.title}: {assignment.title} — {result} ({score_percent}%)"
            body = (
                f"Your submission for '{assignment.title}' in '{course.title}' "
                f"was graded: {result} ({score_percent}%).\n\nFeedback:\n{feedback}"
            )
            self._mail.enqueue_notify(
                NotifyMailMessage(
                    kind="notify",
                    to=to_addr,
                    subject=subject,
                    body=body,
                )
            )
        except Exception:
            logger.exception(
                "Grade notify enqueue failed",
                extra={
                    "assignment_id": assignment_id,
                    "submission_id": submission_id,
                },
            )

    def _require_owned_draft(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> SubmissionRow:
        course = self._get_course(course_id)
        assignment = self._get_assignment_or_404(course_id, assignment_id)
        if assignment.status != "published":
            raise NotFound("Assignment not found")
        self._ensure_student_access(
            course_id=course_id,
            module_id=assignment.module_id,
            cognito_sub=cognito_sub,
            role=role,
            course=course,
        )
        if not _is_valid_uuid(submission_id):
            raise NotFound("Submission not found")
        submission = self._repo.get_submission(
            course_id=course_id,
            assignment_id=assignment_id,
            submission_id=submission_id,
        )
        if submission is None or submission.user_sub != cognito_sub:
            raise NotFound("Submission not found")
        if submission.status != "draft":
            raise Conflict("Submission is not a draft", code="not_draft")
        return submission

    def _require_submission_access(
        self,
        course_id: str,
        assignment_id: str,
        submission_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> SubmissionRow:
        course = self._get_course(course_id)
        assignment = self._get_assignment_or_404(course_id, assignment_id)
        can_modify = self._can_modify_course(course, cognito_sub=cognito_sub, role=role)
        if not can_modify:
            if assignment.status != "published":
                raise NotFound("Assignment not found")
            self._ensure_student_access(
                course_id=course_id,
                module_id=assignment.module_id,
                cognito_sub=cognito_sub,
                role=role,
                course=course,
            )
        if not _is_valid_uuid(submission_id):
            raise NotFound("Submission not found")
        submission = self._repo.get_submission(
            course_id=course_id,
            assignment_id=assignment_id,
            submission_id=submission_id,
        )
        if submission is None:
            raise NotFound("Submission not found")
        if not can_modify and submission.user_sub != cognito_sub:
            raise NotFound("Submission not found")
        return submission
