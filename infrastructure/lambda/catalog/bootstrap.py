"""Composition root for the catalog Lambda.



Responsibilities:

  * Load configuration once per warm Lambda container.

  * Wire PostgreSQL repository adapters (RDS only).

  * Build the domain services and cache them in module state so subsequent

    invocations reuse the same objects (the connection is created lazily on the

    first query and cached for the lifetime of the warm container).



Nothing here talks to AWS SDKs directly except inside the private

``_build_rds_connection_factory`` helper, which is the only place Secrets

Manager and ``psycopg2.connect`` are called. Tests patch that helper (or the

module-level ``_secretsmanager_client`` / ``_psycopg2_connect`` hooks it uses)

to exercise the wiring without network access.

"""



from __future__ import annotations



import json

from dataclasses import dataclass

from typing import Any, Callable, Dict, Optional, Tuple



from config import AppConfig, load_config

from services.auth.rds_repo import UserProfileRdsRepository

from services.auth.service import UserProfileService

from services.course_management.models import Course

from services.course_management.image_storage import CourseImageStorage

from services.course_management.rds_repo import CourseCatalogRdsRepository

from services.course_management.service import CourseManagementService

from services.course_management.storage import CourseMediaStorage, LessonFileStorage

from services.course_management.video_providers.kinescope_adapter import KinescopeVideoAdapter

from services.course_management.video_providers.port import VideoProviderPort

from services.course_management.video_providers.s3_video_provider import S3VideoProvider

from services.course_management.video_providers.vdocipher_adapter import VdocipherVideoAdapter

from services.progress.rds_repo import LessonProgressRdsRepository

from services.progress.service import LessonProgressService

from services.lesson_notes import LessonNotesRdsRepository, LessonNotesService

from services.assignments import (

    AssignmentsRdsRepository,

    AssignmentsService,

    AssignmentFileStorage,

)

from services.assignments.ports import CourseOwnerInfo, NotifyMailMessage

from services.certificates.eligibility import AssignmentRequirement, QuizRequirement

from services.certificates.entitlement import is_certificate_entitled

from services.certificates.ports import CourseInfo as CertificateCourseInfo

from services.certificates.rds_repo import CertificatesRdsRepository

from services.certificates.service import CertificatesService

from services.research_team.rds_repo import ResearchTeamRdsRepository

from services.research_team.service import ResearchTeamService

from services.purchases.checkout_service import PurchaseCheckoutService

from services.purchases.manage_service import PurchaseManageService

from services.purchases.repo import PurchaseRdsRepository

from services.purchases.service import CourseAccessService

from services.question_banks.rds_repo import QuestionBankRdsRepository

from services.rate_limit.rds_repo import RateLimitRdsRepository

from services.rate_limit.service import RateLimitService

from services.contact.service import ContactService

from services.common.sqs_client import send_media_cleanup_job, send_transactional_mail_job

from services.question_banks.service import QuestionBankService

from services.question_banks.gating import (
    DEFAULT_MODULE_QUIZ_PASS_PERCENT,
    module_is_locked_for_student,
    module_is_passed,
)

from services.question_banks.visibility import (

    apply_module_quiz_visibility,

    module_quiz_score_percent,

)





@dataclass(frozen=True)

class _ModuleQuizVisibilityAdapter:

    """Composition-root adapter: ``ModuleQuizVisibilityPort`` → question bank RDS + visibility."""



    _qb_repo: QuestionBankRdsRepository



    def module_quiz_visibility_by_course(

        self,

        course_id: str,

        *,

        course_status: str,

        has_lesson_access: bool,

        cognito_sub: str,

    ) -> Dict[str, Dict[str, Any]]:

        if course_status != "PUBLISHED" or not has_lesson_access:

            return {}

        repo_map = self._qb_repo.list_module_quiz_visibility_for_course(

            course_id=course_id

        )

        visibility = apply_module_quiz_visibility(

            repo_map,

            course_status=course_status,

            has_lesson_access=has_lesson_access,

        )

        if not visibility:

            return visibility

        pass_map = self._qb_repo.list_module_quiz_pass_percent_for_course(

            course_id=course_id

        )

        visible_ids = set(visibility.keys())

        for module_id, entry in visibility.items():

            entry["passPercent"] = pass_map.get(

                module_id, DEFAULT_MODULE_QUIZ_PASS_PERCENT

            )

        user_sub = cognito_sub.strip()

        if not user_sub:

            for entry in visibility.values():

                entry["passed"] = False

            return visibility

        raw_scores = self._qb_repo.list_submitted_attempt_scores_by_module(

            course_id=course_id,

            user_sub=user_sub,

        )

        submitted_by_module = {

            mod: [

                (row["correctCount"], row["totalCount"]) for row in attempts

            ]

            for mod, attempts in raw_scores.items()

        }

        for module_id, entry in visibility.items():

            entry["passed"] = module_is_passed(

                module_id=module_id,

                visible_quiz_module_ids=visible_ids,

                pass_percent_by_module_id=pass_map,

                submitted_scores_by_module_id=submitted_by_module,

            )

        scores = self._qb_repo.list_latest_submission_scores_for_course(

            course_id=course_id,

            user_sub=user_sub,

        )

        for module_id, entry in visibility.items():

            score = scores.get(module_id)

            if score is None:

                continue

            entry["latestScorePercent"] = module_quiz_score_percent(

                correct_count=score["correctCount"],

                total_count=score["totalCount"],

            )

        return visibility





@dataclass(frozen=True)

class _CourseMutateAuthorizerAdapter:

    """Composition-root adapter: ``CourseMutateAuthorizerPort`` → ``CourseManagementService``."""



    _course: CourseManagementService



    def ensure_course_mutable_by_actor(

        self, course_id: str, *, cognito_sub: str, role: str

    ) -> None:

        self._course.ensure_can_modify_course(

            course_id, cognito_sub=cognito_sub, role=role

        )



    def ensure_course_publisher_read_scope(

        self, course_id: str, *, cognito_sub: str, role: str

    ) -> None:

        self._course.ensure_publisher_question_bank_read(

            course_id, cognito_sub=cognito_sub, role=role

        )





@dataclass(frozen=True)

class _CourseReadAdapter:

    """Composition-root adapter: ``CourseReadPort`` → course catalog RDS."""



    _course_repo: CourseCatalogRdsRepository



    def get_course_status(self, course_id: str) -> str | None:

        course = self._course_repo.get_course(course_id)

        return course.status if course else None





@dataclass(frozen=True)

class _StudentLessonAccessAdapter:

    """Composition-root adapter: ``StudentLessonAccessPort`` → ``CourseManagementService``."""



    _course: CourseManagementService

    _course_repo: CourseCatalogRdsRepository



    def viewer_has_lesson_access(

        self, course_id: str, cognito_sub: str, role: str

    ) -> bool:

        course: Course | None = self._course_repo.get_course(course_id)

        if course is None:

            return False

        return self._course.viewer_has_lesson_access(

            course,

            course_id=course_id,

            cognito_sub=cognito_sub,

            role=role,

        )





@dataclass(frozen=True)

class _StudentModuleLockAdapter:

    """Composition-root adapter: ``StudentModuleLockPort`` → catalog RDS + gating."""



    _course_repo: CourseCatalogRdsRepository

    _qb_repo: QuestionBankRdsRepository

    _course_access: CourseAccessService



    def is_module_locked_for_student(

        self,

        course_id: str,

        module_id: str,

        *,

        cognito_sub: str,

        role: str,

    ) -> bool:

        cid = (course_id or "").strip()

        mid = (module_id or "").strip()

        if not cid or not mid:

            return False

        course = self._course_repo.get_course(cid)

        if course is None:

            return False

        if self._course_access.bypasses_module_lock(

            cognito_sub, cid, role, course=course

        ):

            return False

        modules = self._course_repo.list_course_modules(cid)

        ordered_module_ids = [

            m.id for m in sorted(modules, key=lambda row: row.order)

        ]

        if mid not in ordered_module_ids:

            return False

        visibility = self._qb_repo.list_module_quiz_visibility_for_course(

            course_id=cid

        )

        pass_percent_by_module_id = (

            self._qb_repo.list_module_quiz_pass_percent_for_course(course_id=cid)

        )

        raw_scores = self._qb_repo.list_submitted_attempt_scores_by_module(

            course_id=cid,

            user_sub=(cognito_sub or "").strip(),

        )

        submitted_scores_by_module_id = {

            mod: [

                (entry["correctCount"], entry["totalCount"]) for entry in attempts

            ]

            for mod, attempts in raw_scores.items()

        }

        return module_is_locked_for_student(

            ordered_module_ids,

            target_module_id=mid,

            visible_quiz_module_ids=set(visibility.keys()),

            pass_percent_by_module_id=pass_percent_by_module_id,

            submitted_scores_by_module_id=submitted_scores_by_module_id,

        )





@dataclass(frozen=True)

class _AssignmentCourseLookupAdapter:

    """Composition-root adapter: assignments ``CourseLookupPort`` → course catalog RDS."""



    _course_repo: CourseCatalogRdsRepository



    def get_course(self, course_id: str) -> CourseOwnerInfo | None:

        course = self._course_repo.get_course(course_id)

        if course is None:

            return None

        return CourseOwnerInfo(id=course.id, title=course.title, created_by=course.createdBy)



    def module_belongs_to_course(self, course_id: str, module_id: str) -> bool:

        return self._course_repo.get_course_module(course_id, module_id) is not None





@dataclass(frozen=True)

class _AssignmentMediaCleanupAdapter:

    """Composition-root adapter: assignments ``MediaCleanupPort`` → SQS media cleanup."""



    _queue_url: str



    def queue_url(self) -> str:

        return (self._queue_url or "").strip()



    def enqueue_object_keys(self, keys) -> None:

        cleaned = [k.strip() for k in keys if k and str(k).strip()]

        if not cleaned:

            return

        course_id = cleaned[0].split("/", 1)[0]

        send_media_cleanup_job(self.queue_url(), course_id, cleaned)





@dataclass(frozen=True)

class _AssignmentMailAdapter:

    """Composition-root adapter: assignments ``AssignmentMailPort`` → transactional mail SQS."""



    _queue_url: str



    def enqueue_notify(self, message: NotifyMailMessage) -> None:

        send_transactional_mail_job(

            (self._queue_url or "").strip(),

            {

                "kind": message.kind,

                "to": message.to,

                "subject": message.subject,

                "bodyText": message.body,

            },

        )





@dataclass(frozen=True)

class _UserEmailAdapter:

    """Composition-root adapter: assignments ``UserEmailPort`` → users.email."""



    _auth_repo: UserProfileRdsRepository



    def get_email_for_user_sub(self, user_sub: str) -> str:

        profile = self._auth_repo.get_profile(user_sub)

        if not profile:

            return ""

        return str(profile.get("email") or "")





@dataclass(frozen=True)

class _ResearchTeamCertificateAdapter:

    """Composition-root adapter: research_team cert lookup → certificates repo."""



    _repo: CertificatesRdsRepository



    def get_status_for_user_course(self, user_sub: str, course_id: str) -> Optional[str]:

        row = self._repo.get_by_user_course(user_sub, course_id)

        if row is None:

            return None

        return str(row.status)





@dataclass(frozen=True)

class _CertificateCourseLookupAdapter:

    """Composition-root adapter: certificates course lookup → catalog RDS."""



    _course_repo: CourseCatalogRdsRepository



    def get_course(self, course_id: str) -> CertificateCourseInfo | None:

        course = self._course_repo.get_course(course_id)

        if course is None:

            return None

        return CertificateCourseInfo(

            id=course.id,

            title=course.title,

            created_by=course.createdBy,

            certificate_code=course.certificateCode,

        )





@dataclass(frozen=True)

class _CertificateProfileAdapter:

    """Composition-root adapter: certificates profile names → users table."""



    _auth_repo: UserProfileRdsRepository



    def get_given_and_family_name(self, user_sub: str) -> tuple[str, str]:

        profile = self._auth_repo.get_profile(user_sub)

        if not profile:

            return "", ""

        return (

            str(profile.get("givenName") or ""),

            str(profile.get("familyName") or ""),

        )





@dataclass(frozen=True)

class _CertificateRequirementsAdapter:

    """Visible quizzes + assignment pass state for certificate eligibility."""



    _qb_repo: QuestionBankRdsRepository

    _assignments_repo: AssignmentsRdsRepository



    def get_requirements(

        self, course_id: str, user_sub: str

    ) -> tuple[list[QuizRequirement], list[AssignmentRequirement]]:

        visible = self._qb_repo.list_module_quiz_visibility_for_course(course_id=course_id)

        pass_by_module = self._qb_repo.list_module_quiz_pass_percent_for_course(

            course_id=course_id

        )

        scores_by_module = self._qb_repo.list_submitted_attempt_scores_by_module(

            course_id=course_id, user_sub=user_sub

        )

        submitted: dict[str, list[tuple[int, int]]] = {

            module_id: [

                (int(a["correctCount"]), int(a["totalCount"])) for a in attempts

            ]

            for module_id, attempts in scores_by_module.items()

        }

        visible_ids = set(visible.keys())

        quizzes: list[QuizRequirement] = []

        for module_id in visible:

            passed = module_is_passed(

                module_id=module_id,

                visible_quiz_module_ids=visible_ids,

                pass_percent_by_module_id=pass_by_module,

                submitted_scores_by_module_id=submitted,

            )

            quizzes.append(QuizRequirement(module_id=module_id, passed=passed))



        assignments: list[AssignmentRequirement] = []

        for row in self._assignments_repo.list_assignments(course_id):

            submission = self._assignments_repo.get_latest_submission_for_user(

                assignment_id=row.id, user_sub=user_sub

            )

            passed = bool(

                submission is not None

                and submission.grade is not None

                and submission.grade.passed

            )

            assignments.append(

                AssignmentRequirement(

                    assignment_id=row.id,

                    status=row.status,

                    counts_toward_certificate=row.counts_toward_certificate,

                    passed=passed,

                )

            )

        return quizzes, assignments





def _certificate_has_course_activity(

    qb_repo: QuestionBankRdsRepository,

    assignments_repo: AssignmentsRdsRepository,

) -> Callable[[str, str], bool]:

    """True when this student already submitted a quiz attempt or assignment on the course."""



    def has_activity(user_sub: str, course_id: str) -> bool:

        scores = qb_repo.list_submitted_attempt_scores_by_module(

            course_id=course_id,

            user_sub=user_sub,

        )

        if scores:

            return True

        return assignments_repo.user_has_submission_for_course(

            course_id=course_id,

            user_sub=user_sub,

        )



    return has_activity





@dataclass(frozen=True)

class _CertificateEntitledAdapter:

    """Paid course purchase (any status), or a paid bundle of a published course.



    Teacher and admin ownership is not an entitlement. ``CourseAccessService``

    stays on playback and quizzes; this adapter does not call it.

    """



    _course_repo: CourseCatalogRdsRepository

    _purchase_repo: PurchaseRdsRepository

    _has_course_activity: Optional[Callable[[str, str], bool]] = None



    def _course_activity(self, user_sub: str, course_id: str) -> bool:

        if self._has_course_activity is None:

            return False

        return self._has_course_activity(user_sub, course_id)



    def _is_entitled_course(

        self,

        user_sub: str,

        course: Course,

        *,

        paid_bundle: bool,

    ) -> bool:

        paid_course = self._purchase_repo.has_paid_course_purchase(user_sub, course.id)

        published = course.status == "PUBLISHED"

        activity = False

        if paid_bundle and not published and not paid_course:

            activity = self._course_activity(user_sub, course.id)

        return is_certificate_entitled(

            has_paid_course_purchase=paid_course,

            has_paid_bundle=paid_bundle,

            course_published=published,

            has_course_activity=activity,

        )



    def is_entitled(self, user_sub: str, course_id: str) -> bool:

        course = self._course_repo.get_course(course_id)

        if course is None:

            return False

        paid_bundle = self._purchase_repo.has_paid_bundle(user_sub)

        return self._is_entitled_course(

            user_sub,

            course,

            paid_bundle=paid_bundle,

        )



    def list_entitled_course_ids(self, user_sub: str) -> list[str]:

        paid_bundle = self._purchase_repo.has_paid_bundle(user_sub)

        out: list[str] = []

        for course in self._course_repo.list_courses():

            if self._is_entitled_course(user_sub, course, paid_bundle=paid_bundle):

                out.append(course.id)

        return out





@dataclass(frozen=True)

class AwsDeps:

    cfg: AppConfig

    service: CourseManagementService

    auth_service: UserProfileService

    auth_repo: UserProfileRdsRepository

    progress_service: LessonProgressService

    question_bank_service: QuestionBankService

    purchase_checkout_service: PurchaseCheckoutService

    purchase_manage_service: PurchaseManageService

    rate_limit_service: RateLimitService

    contact_service: ContactService

    lesson_notes_service: LessonNotesService

    assignments_service: Optional[AssignmentsService]

    certificates_service: CertificatesService

    research_team_service: ResearchTeamService





_cached: Dict[str, Any] = {}





ConnectionFactory = Callable[[], Any]





def _secretsmanager_client() -> Any:

    import boto3



    return boto3.client("secretsmanager")





def _psycopg2_connect(**kwargs: Any) -> Any:

    import psycopg2



    conn = psycopg2.connect(**kwargs)

    # Default to autocommit so a read-only `_execute(commit=False)` does not

    # leave the connection idle in a transaction holding share locks across

    # warm Lambda invocations. Repository methods that need multi-statement

    # atomicity (e.g. CourseCatalogRdsRepository.create_course,

    # set_lesson_orders) explicitly toggle autocommit off via

    # `_atomic_transaction` for the duration of their block.

    conn.autocommit = True

    return conn





def _rds_config_complete(cfg: AppConfig) -> bool:

    return bool(cfg.db_host and cfg.db_name and cfg.db_secret_arn)





def _build_rds_connection_factory(cfg: AppConfig) -> ConnectionFactory:

    """Return a ``() -> connection`` callable that lazily opens a PostgreSQL

    connection using credentials fetched from Secrets Manager.



    The factory is called at most once per warm Lambda container (caching in

    the repo adapters themselves), so the Secrets Manager fetch happens on the

    first query rather than at cold-start import time. This keeps import cheap

    when the Lambda is invoked but does not touch RDS.

    """

    if not cfg.db_secret_arn:

        raise RuntimeError("DB_SECRET_ARN is required for the RDS catalog")

    if not cfg.db_host:

        raise RuntimeError("DB_HOST is required for the RDS catalog")

    if not cfg.db_name:

        raise RuntimeError("DB_NAME is required for the RDS catalog")



    def factory() -> Any:

        sm = _secretsmanager_client()

        response = sm.get_secret_value(SecretId=cfg.db_secret_arn)

        payload_raw = response.get("SecretString") or ""

        try:

            payload = json.loads(payload_raw)

        except json.JSONDecodeError as exc:

            raise RuntimeError("RDS secret is not valid JSON") from exc

        user = str(payload.get("username") or "")

        password = str(payload.get("password") or "")

        if not user or not password:

            raise RuntimeError("RDS secret missing username/password fields")

        return _psycopg2_connect(

            host=cfg.db_host,

            port=int(cfg.db_port or 5432),

            dbname=cfg.db_name,

            user=user,

            password=password,

            sslmode="require",

            connect_timeout=5,

            # Server-side single-statement cap. A wedged query raises

            # psycopg2.errors.QueryCanceled at 10s instead of stalling the warm

            # container until the Lambda hard timeout, letting the repo-layer

            # OperationalError retry path open a fresh connection if needed.

            options="-c statement_timeout=10000",

        )



    return factory





def _build_video_provider(cfg: AppConfig, video_storage: CourseMediaStorage) -> VideoProviderPort:

    provider = (cfg.video_provider or "kinescope").strip().lower()

    if provider == "s3":

        return S3VideoProvider(video_storage)

    if provider == "kinescope":

        return KinescopeVideoAdapter(

            api_token=cfg.kinescope_api_token,

            parent_id=cfg.kinescope_parent_id,

        )

    if provider == "vdocipher":

        return VdocipherVideoAdapter()

    raise RuntimeError(f"Unsupported VIDEO_PROVIDER: {cfg.video_provider!r}")





def get_cached_aws_deps() -> Optional[AwsDeps]:

    dep = _cached.get("aws")

    return dep if isinstance(dep, AwsDeps) else None





def build_aws_deps(cfg: AppConfig) -> AwsDeps:

    if not _rds_config_complete(cfg):

        raise RuntimeError(

            "RDS catalog requires DB_HOST, DB_NAME, and DB_SECRET_ARN to be set"

        )



    conn_factory = _build_rds_connection_factory(cfg)

    course_repo = CourseCatalogRdsRepository(conn_factory)

    purchase_repo = PurchaseRdsRepository(

        conn_factory,

        deployment_environment=cfg.deployment_environment,

    )

    course_access = CourseAccessService(purchase_repo, course_repo)

    auth_repo = UserProfileRdsRepository(conn_factory)

    progress_repo = LessonProgressRdsRepository(conn_factory)



    storage = CourseMediaStorage(cfg.video_bucket) if cfg.video_bucket else None

    file_storage = LessonFileStorage(cfg.video_bucket) if cfg.video_bucket else None

    image_storage = CourseImageStorage(cfg.video_bucket) if cfg.video_bucket else None

    video_provider = _build_video_provider(cfg, storage) if storage is not None else None

    qb_repo = QuestionBankRdsRepository(conn_factory)

    module_quiz_visibility = _ModuleQuizVisibilityAdapter(qb_repo)

    module_lock = _StudentModuleLockAdapter(

        course_repo,

        qb_repo,

        course_access,

    )

    assignments_repo = AssignmentsRdsRepository(conn_factory)



    service = CourseManagementService(

        course_repo,

        image_storage,

        file_storage=file_storage,

        course_access=course_access,

        video_provider=video_provider,

        media_cleanup_queue_url=cfg.media_cleanup_queue_url,

        module_quiz_visibility=module_quiz_visibility,

        module_lock=module_lock,

        assignment_media_keys=assignments_repo,

        kinescope_drm_jwt_secret=cfg.kinescope_drm_jwt_secret,

        kinescope_drm_jwt_issuer=cfg.kinescope_drm_jwt_issuer,

        kinescope_drm_jwt_audience=cfg.kinescope_drm_jwt_audience,

        kinescope_api_token=cfg.kinescope_api_token,

        deployment_environment=cfg.deployment_environment,

    )

    certificates_repo = CertificatesRdsRepository(conn_factory)

    certificate_entitlement = _CertificateEntitledAdapter(

        course_repo,

        purchase_repo,

        _certificate_has_course_activity(qb_repo, assignments_repo),

    )

    certificates_service = CertificatesService(

        certificates_repo,

        certificate_entitlement,

        _CertificateCourseLookupAdapter(course_repo),

        _CertificateProfileAdapter(auth_repo),

        _CertificateRequirementsAdapter(qb_repo, assignments_repo),

        certificate_entitlement,

    )

    auth_service = UserProfileService(

        auth_repo,

        certificate_issuer=certificates_service,

    )

    progress_service = LessonProgressService(

        progress_repo,

        course_access,

        course_repo,

        progress_complete_ratio=cfg.progress_complete_ratio,

        position_slack_sec=cfg.progress_position_slack_sec,

        module_lock=module_lock,

    )

    notes_repo = LessonNotesRdsRepository(conn_factory)

    lesson_notes_service = LessonNotesService(

        notes_repo,

        course_access,

        course_repo,

        module_lock=module_lock,

    )



    if cfg.video_bucket:

        assignment_storage = AssignmentFileStorage(cfg.video_bucket)

        assignments_service = AssignmentsService(

            assignments_repo,

            assignment_storage,

            course_access,

            module_lock,

            _AssignmentCourseLookupAdapter(course_repo),

            _AssignmentMediaCleanupAdapter(cfg.media_cleanup_queue_url),

            _AssignmentMailAdapter(cfg.transactional_mail_queue_url),

            _UserEmailAdapter(auth_repo),

            certificate_issuer=certificates_service,

        )

    else:

        assignments_service = None



    research_team_repo = ResearchTeamRdsRepository(conn_factory)

    research_team_service = ResearchTeamService(

        research_team_repo,

        _ResearchTeamCertificateAdapter(certificates_repo),

        _UserEmailAdapter(auth_repo),

        _AssignmentMailAdapter(cfg.transactional_mail_queue_url),

    )



    authorizer = _CourseMutateAuthorizerAdapter(service)

    course_read = _CourseReadAdapter(course_repo)

    lesson_access = _StudentLessonAccessAdapter(service, course_repo)

    question_bank_service = QuestionBankService(

        course_mutate_authorizer=authorizer,

        question_bank_repo=qb_repo,

        student_lesson_access=lesson_access,

        course_read=course_read,

        module_lock=module_lock,

        certificate_issuer=certificates_service,

    )

    purchase_checkout_service = PurchaseCheckoutService(purchase_repo)

    purchase_manage_service = PurchaseManageService(

        purchase_repo,

        course_repo,

        billing_teacher_sub=cfg.billing_teacher_sub,

    )

    rate_limit_repo = RateLimitRdsRepository(conn_factory)

    rate_limit_service = RateLimitService(

        rate_limit_repo,

        max_overrides=cfg.rate_limit_max_overrides,

    )

    contact_service = ContactService(

        queue_url=cfg.transactional_mail_queue_url,

        enqueue=lambda url, payload: send_transactional_mail_job(url, payload),

    )



    return AwsDeps(

        cfg=cfg,

        service=service,

        auth_service=auth_service,

        auth_repo=auth_repo,

        progress_service=progress_service,

        question_bank_service=question_bank_service,

        purchase_checkout_service=purchase_checkout_service,

        purchase_manage_service=purchase_manage_service,

        rate_limit_service=rate_limit_service,

        contact_service=contact_service,

        lesson_notes_service=lesson_notes_service,

        assignments_service=assignments_service,

        certificates_service=certificates_service,

        research_team_service=research_team_service,

    )





def warm_aws_deps_if_needed(cfg: AppConfig) -> None:

    if not _rds_config_complete(cfg):

        return

    if "aws" not in _cached:

        _cached["aws"] = build_aws_deps(cfg)





def lambda_bootstrap() -> Tuple[

    AppConfig,

    Optional[CourseManagementService],

    Optional[UserProfileService],

    Optional[UserProfileRdsRepository],

    Optional[LessonProgressService],

    Optional[QuestionBankService],

    Optional[PurchaseManageService],

    Optional[RateLimitService],

]:

    """

    Composition root: load config and construct dependencies once.

    When RDS settings are incomplete the catalog cannot be wired, so

    ``(cfg, None, …)`` (eight ``None`` service slots) is returned and the handler responds

    with a configuration error.

    """

    cfg = load_config()

    if not _rds_config_complete(cfg):

        return cfg, None, None, None, None, None, None, None



    existing = get_cached_aws_deps()

    if existing is not None:

        return (

            existing.cfg,

            existing.service,

            existing.auth_service,

            existing.auth_repo,

            existing.progress_service,

            existing.question_bank_service,

            existing.purchase_manage_service,

            existing.rate_limit_service,

        )



    deps = build_aws_deps(cfg)

    _cached["aws"] = deps

    return (

        deps.cfg,

        deps.service,

        deps.auth_service,

        deps.auth_repo,

        deps.progress_service,

        deps.question_bank_service,

        deps.purchase_manage_service,

        deps.rate_limit_service,

    )


