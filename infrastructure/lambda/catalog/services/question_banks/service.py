"""Application service for question banks and module quizzes."""

from __future__ import annotations

import json
import random
from typing import Any
from uuid import UUID

from services.common.errors import BadRequest, Conflict, NotFound
from services.question_banks.binding_draw import draw_question_ids
from services.question_banks.grading import (
    GradingRow,
    QuizGradeResult,
    grade_bound_answers,
)
from services.question_banks.mcq_validation import (
    validate_correct_option_key,
    validate_draft_question_for_publish,
    validate_mcq_options_json,
)
from services.question_banks.models import (
    ModuleQuiz,
    ModuleQuizAttempt,
    PublishedQuestionGradingRow,
    Question,
    QuestionBank,
    StudentModuleQuizBinding,
)
from services.question_banks.presentation_shuffle import (
    apply_presentation_shuffle,
    shuffle_choice_orders_for_questions,
    shuffle_question_order,
    validate_question_order,
)
from services.question_banks.ports import (
    CourseMutateAuthorizerPort,
    CourseReadPort,
    StudentLessonAccessPort,
)
from services.question_banks.rds_repo import QuestionBankRdsRepository

_QUESTION_BANK_NAME_MAX_LENGTH = 80


class QuestionBankService:
    def __init__(
        self,
        *,
        course_mutate_authorizer: CourseMutateAuthorizerPort,
        question_bank_repo: QuestionBankRdsRepository,
        student_lesson_access: StudentLessonAccessPort,
        course_read: CourseReadPort,
    ) -> None:
        self._authorizer = course_mutate_authorizer
        self._repo = question_bank_repo
        self._lesson_access = student_lesson_access
        self._course_read = course_read

    def start_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
        retake: bool = False,
        rng: random.Random | None = None,
    ) -> dict[str, Any]:
        module_quiz = self._resolve_startable_module_quiz(
            course_id, module_id, cognito_sub=cognito_sub, role=role
        )
        user_sub = cognito_sub.strip()
        binding = self._repo.get_binding_for_student(
            module_quiz_id=module_quiz.id, user_sub=user_sub
        )
        if binding is None:
            binding = self._create_binding_for_student(
                module_quiz,
                course_id=course_id,
                user_sub=user_sub,
                rng=rng,
            )

        open_attempt = self._repo.get_open_attempt(binding_id=binding.id)
        if open_attempt is not None:
            return self._student_quiz_start_in_progress(
                module_quiz, binding, open_attempt
            )

        latest = self._repo.get_latest_attempt(binding_id=binding.id)
        if latest is not None and latest.status == "submitted" and not retake:
            return self._student_quiz_start_latest_results(module_quiz, binding)

        shuffle_rng = rng if rng is not None else random.Random()
        if latest is not None and latest.status == "in_progress":
            attempt = latest
        else:
            attempt = self._insert_new_attempt(
                binding, latest=latest, rng=shuffle_rng
            )
        return self._student_quiz_start_in_progress(module_quiz, binding, attempt)

    def submit_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
        attempt_id: str,
        answers: dict[str, str],
    ) -> dict[str, Any]:
        """Grade bound answers, persist submission, return scored breakdown (QB-H)."""
        self._resolve_startable_module_quiz(
            course_id, module_id, cognito_sub=cognito_sub, role=role
        )
        user_sub = cognito_sub.strip()
        cid = course_id.strip()
        mid = module_id.strip()
        aid = attempt_id.strip()
        ctx = self._repo.get_attempt_with_binding_rows(attempt_id=aid)
        if ctx is None:
            raise NotFound("Module quiz attempt not found")
        if ctx.courseId != cid or ctx.moduleId != mid:
            raise NotFound("Module quiz attempt not found")
        if ctx.userSub != user_sub:
            raise NotFound("Module quiz attempt not found")
        if ctx.attempt.status != "in_progress":
            raise Conflict("Quiz attempt already submitted")
        binding = self._repo.get_binding_for_student(
            module_quiz_id=ctx.moduleQuizId,
            user_sub=user_sub,
        )
        if binding is None or binding.id != ctx.attempt.bindingId:
            raise NotFound("Module quiz attempt not found")
        ordered_ids = binding.questionIds
        grading_rows = self._repo.list_grading_rows_for_questions(
            course_id=cid,
            question_ids=ordered_ids,
        )
        if len(grading_rows) != len(ordered_ids):
            raise Conflict("Module quiz questions could not be loaded")
        grading_by_id, prompts_by_id = self._grading_inputs_from_published_rows(
            grading_rows
        )
        try:
            grade_result = grade_bound_answers(
                question_ids=ordered_ids,
                answers=answers,
                grading_by_question_id=grading_by_id,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        normalized_answers = {
            ga.question_id: ga.selected_option_key
            for ga in grade_result.questions
        }
        try:
            self._repo.insert_submission_and_mark_submitted(
                attempt_id=ctx.attempt.id,
                answers_json=normalized_answers,
                correct_count=grade_result.correct_count,
                total_count=grade_result.total_count,
            )
        except Conflict:
            raise
        except NotFound:
            raise NotFound("Module quiz attempt not found") from None
        return {
            "attemptId": ctx.attempt.id,
            "attemptNumber": ctx.attempt.attemptNumber,
            "correctCount": grade_result.correct_count,
            "totalCount": grade_result.total_count,
            "questions": self._questions_result_breakdown(
                grade_result, prompts_by_id
            ),
        }

    def _resolve_startable_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> ModuleQuiz:
        status = self._course_read.get_course_status(course_id)
        if status != "PUBLISHED":
            raise NotFound("Module quiz not available")
        if not self._lesson_access.viewer_has_lesson_access(
            course_id, cognito_sub, role
        ):
            raise NotFound("Module quiz not available")
        module_quiz = self._repo.get_module_quiz_by_module_id(module_id=module_id)
        if module_quiz is None or module_quiz.courseId != course_id:
            raise NotFound("Module quiz not available")
        bank_id = module_quiz.questionBankId
        served_n = module_quiz.servedCountN
        if not bank_id or served_n is None or served_n < 1:
            raise NotFound("Module quiz not available")
        bank = self._repo.get_question_bank_by_id(bank_id=bank_id)
        if (
            bank is None
            or bank.courseId != course_id
            or bank.status != "PUBLISHED"
        ):
            raise NotFound("Module quiz not available")
        return module_quiz

    def _create_binding_for_student(
        self,
        module_quiz: ModuleQuiz,
        *,
        course_id: str,
        user_sub: str,
        rng: random.Random | None,
    ) -> StudentModuleQuizBinding:
        bank_id = module_quiz.questionBankId
        assert bank_id is not None
        served_n = module_quiz.servedCountN
        assert served_n is not None and served_n >= 1
        published_ids = self._repo.list_published_question_ids(
            course_id=course_id, bank_id=bank_id
        )
        draw_rng = rng if rng is not None else random.Random()
        try:
            drawn_ids = draw_question_ids(published_ids, served_n, draw_rng)
        except ValueError as exc:
            raise Conflict(str(exc)) from exc
        bound_rows = self._repo.list_student_bound_questions(
            course_id=course_id, question_ids=drawn_ids
        )
        if len(bound_rows) != len(drawn_ids):
            raise Conflict("Module quiz questions could not be loaded")
        try:
            question_order = shuffle_question_order(drawn_ids, draw_rng)
            choice_orders = shuffle_choice_orders_for_questions(
                bound_rows, draw_rng
            )
        except ValueError as exc:
            raise Conflict(str(exc)) from exc
        try:
            self._repo.insert_binding_with_questions_and_initial_attempt(
                module_quiz_id=module_quiz.id,
                course_id=course_id,
                user_sub=user_sub,
                question_ids=drawn_ids,
                shuffled_question_order=question_order,
                shuffled_choice_orders=choice_orders,
            )
        except Conflict:
            binding = self._repo.get_binding_for_student(
                module_quiz_id=module_quiz.id, user_sub=user_sub
            )
            if binding is None:
                raise
            return binding
        binding = self._repo.get_binding_for_student(
            module_quiz_id=module_quiz.id, user_sub=user_sub
        )
        if binding is None:
            raise Conflict("Module quiz binding could not be loaded after create")
        return binding

    def _insert_new_attempt(
        self,
        binding: StudentModuleQuizBinding,
        *,
        latest: ModuleQuizAttempt | None,
        rng: random.Random,
    ) -> ModuleQuizAttempt:
        attempt_number = 1 if latest is None else latest.attemptNumber + 1
        rows = self._repo.list_student_bound_questions(
            course_id=binding.courseId,
            question_ids=binding.questionIds,
        )
        if len(rows) != len(binding.questionIds):
            raise Conflict("Module quiz questions could not be loaded")
        try:
            question_order = shuffle_question_order(binding.questionIds, rng)
            choice_orders = shuffle_choice_orders_for_questions(rows, rng)
        except ValueError as exc:
            raise Conflict(str(exc)) from exc
        try:
            return self._repo.insert_attempt_with_shuffle(
                binding_id=binding.id,
                attempt_number=attempt_number,
                shuffled_question_order=question_order,
                shuffled_choice_orders=choice_orders,
            )
        except Conflict:
            open_attempt = self._repo.get_open_attempt(binding_id=binding.id)
            if open_attempt is None:
                raise
            return open_attempt

    def _student_quiz_start_in_progress(
        self,
        module_quiz: ModuleQuiz,
        binding: StudentModuleQuizBinding,
        attempt: ModuleQuizAttempt,
    ) -> dict[str, Any]:
        served_n = module_quiz.servedCountN
        assert served_n is not None
        if len(binding.questionIds) != served_n:
            raise Conflict("Module quiz binding is incomplete")
        try:
            validate_question_order(
                binding.questionIds, attempt.shuffledQuestionOrder
            )
        except ValueError as exc:
            raise Conflict(str(exc)) from exc
        rows = self._repo.list_student_bound_questions(
            course_id=binding.courseId,
            question_ids=attempt.shuffledQuestionOrder,
        )
        if len(rows) != served_n:
            raise Conflict("Module quiz questions could not be loaded")
        try:
            questions = apply_presentation_shuffle(
                rows,
                question_order=attempt.shuffledQuestionOrder,
                choice_orders=attempt.shuffledChoiceOrders,
            )
        except ValueError as exc:
            raise Conflict(str(exc)) from exc
        return {
            "phase": "in_progress",
            "moduleQuizId": module_quiz.id,
            "moduleId": module_quiz.moduleId,
            "servedCountN": served_n,
            "attemptId": attempt.id,
            "attemptNumber": attempt.attemptNumber,
            "questionIds": list(attempt.shuffledQuestionOrder),
            "questions": questions,
        }

    def _student_quiz_start_latest_results(
        self,
        module_quiz: ModuleQuiz,
        binding: StudentModuleQuizBinding,
    ) -> dict[str, Any]:
        served_n = module_quiz.servedCountN
        assert served_n is not None
        if len(binding.questionIds) != served_n:
            raise Conflict("Module quiz binding is incomplete")
        snapshot = self._repo.get_latest_submission_for_binding(
            binding_id=binding.id
        )
        if snapshot is None:
            raise Conflict("Quiz submission record not found")
        ordered_ids = binding.questionIds
        grading_rows = self._repo.list_grading_rows_for_questions(
            course_id=binding.courseId,
            question_ids=ordered_ids,
        )
        if len(grading_rows) != len(ordered_ids):
            raise Conflict("Module quiz questions could not be loaded")
        grading_by_id, prompts_by_id = self._grading_inputs_from_published_rows(
            grading_rows
        )
        try:
            grade_result = grade_bound_answers(
                question_ids=ordered_ids,
                answers=snapshot.answersJson,
                grading_by_question_id=grading_by_id,
            )
        except ValueError as exc:
            raise BadRequest(str(exc)) from exc
        return {
            "phase": "latest_results",
            "moduleQuizId": module_quiz.id,
            "moduleId": module_quiz.moduleId,
            "servedCountN": served_n,
            "latestSubmission": {
                "correctCount": snapshot.correctCount,
                "totalCount": snapshot.totalCount,
                "attemptNumber": snapshot.attemptNumber,
                "submittedAt": snapshot.submittedAt,
                "questions": self._questions_result_breakdown(
                    grade_result, prompts_by_id
                ),
            },
        }

    @staticmethod
    def _grading_inputs_from_published_rows(
        rows: list[PublishedQuestionGradingRow],
    ) -> tuple[dict[str, GradingRow], dict[str, str]]:
        grading_by_id: dict[str, GradingRow] = {}
        prompts_by_id: dict[str, str] = {}
        for row in rows:
            opts = _parse_options_json(row.optionsJson)
            grading_by_id[row.id] = GradingRow(
                question_id=row.id,
                correct_option_key=row.correctOptionKey,
                options_json=opts,
            )
            prompts_by_id[row.id] = row.promptText
        return grading_by_id, prompts_by_id

    @staticmethod
    def _questions_result_breakdown(
        grade_result: QuizGradeResult,
        prompts_by_id: dict[str, str],
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": ga.question_id,
                "promptText": prompts_by_id[ga.question_id],
                "selectedOptionKey": ga.selected_option_key,
                "correctOptionKey": ga.correct_option_key,
                "isCorrect": ga.is_correct,
            }
            for ga in grade_result.questions
        ]

    def create_question_bank(
        self, course_id: str, *, name: str, cognito_sub: str, role: str
    ) -> dict[str, str]:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        normalized_name = _validate_question_bank_name(name)
        bank_id = self._repo.insert_question_bank(
            course_id=course_id, name=normalized_name
        )
        return {"questionBankId": bank_id, "name": normalized_name}

    def list_question_banks_for_course(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> list[dict[str, Any]]:
        self._authorizer.ensure_course_publisher_read_scope(
            course_id, cognito_sub=cognito_sub, role=role
        )
        banks = self._repo.list_question_banks_for_course(course_id=course_id)
        return [
            {
                "questionBankId": b.id,
                "name": _question_bank_display_name(b),
                "status": b.status,
                "createdAt": b.createdAt,
                "updatedAt": b.updatedAt,
            }
            for b in banks
        ]

    def rename_question_bank(
        self,
        course_id: str,
        bank_id: str,
        *,
        name: str,
        cognito_sub: str,
        role: str,
    ) -> dict[str, str]:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        normalized_name = _validate_question_bank_name(name)
        self._repo.update_question_bank_name(
            course_id=course_id, bank_id=bank_id, name=normalized_name
        )
        return {"questionBankId": bank_id, "name": normalized_name}

    def list_module_quizzes_for_course(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> list[dict[str, Any]]:
        self._authorizer.ensure_course_publisher_read_scope(
            course_id, cognito_sub=cognito_sub, role=role
        )
        rows = self._repo.list_module_quizzes_for_course(course_id=course_id)
        return [self._publisher_module_quiz_read_dict(mq) for mq in rows]

    @staticmethod
    def _publisher_module_quiz_read_dict(mq: ModuleQuiz) -> dict[str, Any]:
        return {
            "quizId": mq.id,
            "moduleId": mq.moduleId,
            "questionBankId": mq.questionBankId,
            "servedCountN": mq.servedCountN,
            "createdAt": mq.createdAt,
            "updatedAt": mq.updatedAt,
        }

    def list_questions_for_publisher(
        self,
        course_id: str,
        bank_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> list[dict[str, Any]]:
        self._authorizer.ensure_course_publisher_read_scope(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bid = (bank_id or "").strip()
        if not _is_uuid_string(bid):
            raise NotFound("Question bank not found for this course")
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bid)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        rows = self._repo.list_questions_for_course_bank(
            course_id=course_id, bank_id=bid
        )
        return [self._publisher_question_read_dict(q) for q in rows]

    @staticmethod
    def _publisher_question_read_dict(q: Question) -> dict[str, Any]:
        return {
            "questionId": q.id,
            "status": q.status,
            "promptText": q.promptText,
            "optionsJson": _parse_options_json(q.optionsJson),
            "correctOptionKey": q.correctOptionKey,
        }

    def create_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
        question_bank_id: str | None = None,
    ) -> str:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bid = (question_bank_id or "").strip()
        if not bid:
            raise BadRequest("questionBankId is required")
        if not _is_uuid_string(bid):
            raise BadRequest("questionBankId must be a valid UUID")
        bank = self._repo.get_question_bank_by_id(bank_id=bid)
        if bank is None:
            raise BadRequest("questionBankId does not reference a question bank")
        cid = course_id.strip()
        if bank.courseId.strip() != cid:
            raise BadRequest("Question bank does not belong to this course")
        existing = self._repo.get_module_quiz_by_question_bank_id(
            course_id=cid, question_bank_id=bid
        )
        if existing is not None and existing.moduleId.strip() != module_id.strip():
            raise Conflict("Question bank is already linked to another module")
        return self._repo.insert_module_quiz(
            course_id=course_id,
            module_id=module_id,
            question_bank_id=bid,
        )

    def get_bank_for_course(
        self,
        course_id: str,
        bank_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> QuestionBank:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        return bank

    def create_draft_question(
        self,
        course_id: str,
        bank_id: str,
        *,
        prompt_text: str,
        options_json: Any,
        correct_option_key: str | None,
        cognito_sub: str,
        role: str,
    ) -> str:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        if bank.status != "DRAFT":
            raise BadRequest(
                "Draft questions can only be created when the bank is in DRAFT status"
            )
        text = (prompt_text or "").strip()
        if not text:
            raise BadRequest("promptText must not be empty")
        validate_mcq_options_json(options_json)
        validate_correct_option_key(
            correct_option_key, options_json=options_json
        )
        return self._repo.insert_draft_question(
            course_id=course_id,
            bank_id=bank_id,
            prompt_text=text,
            options_json=options_json,
            correct_option_key=correct_option_key,
        )

    def publish_question_bank(
        self,
        course_id: str,
        bank_id: str,
        module_id: str,
        n: int,
        *,
        cognito_sub: str,
        role: str,
    ) -> None:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        if bank.status != "DRAFT":
            raise Conflict("Question bank is not in DRAFT status")
        if n < 1:
            raise BadRequest("N must be at least 1")
        drafts = self._repo.list_draft_questions(bank_id=bank_id)
        if len(drafts) == 0:
            raise BadRequest("Cannot publish: question bank has no draft questions")
        if n > len(drafts):
            raise BadRequest(
                "Cannot publish: N is greater than the number of draft questions"
            )
        for q in drafts:
            validate_draft_question_for_publish(
                correct_option_key=q.correctOptionKey,
                options_json=q.optionsJson,
            )
        self._repo.publish_bank_transaction(
            course_id=course_id,
            bank_id=bank_id,
            module_id=module_id,
            n=n,
        )

    def add_published_question(
        self,
        course_id: str,
        bank_id: str,
        *,
        cognito_sub: str,
        role: str,
        prompt_text: str,
        options_json: Any,
        correct_option_key: str,
    ) -> str:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        if bank.status != "PUBLISHED":
            raise BadRequest(
                "Published questions can only be added when the bank is published"
            )
        text = (prompt_text or "").strip()
        if not text:
            raise BadRequest("promptText must not be empty")
        validate_mcq_options_json(options_json)
        key = (correct_option_key or "").strip()
        if not key:
            raise BadRequest("correctOptionKey must not be empty")
        validate_correct_option_key(key, options_json=options_json)
        return self._repo.insert_published_question(
            course_id=course_id,
            bank_id=bank_id,
            prompt_text=text,
            options_json=options_json,
            correct_option_key=key,
        )

    def update_question(
        self,
        course_id: str,
        bank_id: str,
        question_id: str,
        *,
        cognito_sub: str,
        role: str,
        prompt_text: str | None = None,
        options_json: Any = None,
        correct_option_key: str | None = None,
    ) -> None:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        existing = self._repo.get_question_by_id(
            bank_id=bank_id, question_id=question_id
        )
        if existing is None or existing.courseId != course_id:
            raise NotFound("Question not found for this bank")
        if existing.status == "PUBLISHED":
            raise Conflict("Published questions cannot be updated")
        merged_options = (
            options_json if options_json is not None else existing.optionsJson
        )
        merged_correct = (
            correct_option_key
            if correct_option_key is not None
            else existing.correctOptionKey
        )
        if options_json is not None:
            validate_mcq_options_json(options_json)
        if options_json is not None or correct_option_key is not None:
            validate_correct_option_key(merged_correct, options_json=merged_options)
        self._repo.update_question(
            course_id=course_id,
            bank_id=bank_id,
            question_id=question_id,
            prompt_text=prompt_text,
            options_json=options_json,
            correct_option_key=correct_option_key,
        )

    def delete_question(
        self,
        course_id: str,
        bank_id: str,
        question_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> None:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        existing = self._repo.get_question_by_id(
            bank_id=bank_id, question_id=question_id
        )
        if existing is None or existing.courseId != course_id:
            raise NotFound("Question not found for this bank")
        if existing.status == "PUBLISHED":
            raise Conflict("Published questions cannot be deleted")
        self._repo.delete_question(
            course_id=course_id,
            bank_id=bank_id,
            question_id=question_id,
        )


def _parse_options_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw


def _validate_question_bank_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized:
        raise BadRequest("name must not be empty")
    if len(normalized) > _QUESTION_BANK_NAME_MAX_LENGTH:
        raise BadRequest(
            f"name must be {_QUESTION_BANK_NAME_MAX_LENGTH} characters or fewer"
        )
    return normalized


def _question_bank_display_name(bank: QuestionBank) -> str:
    name = (bank.name or "").strip()
    if name:
        return name
    return f"Question bank {bank.id[:8]}"


def _is_uuid_string(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False
