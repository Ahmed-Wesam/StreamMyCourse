import { httpDelete, httpGet, httpPatch, httpPost } from './client'
import type {
  CreateModuleQuizBody,
  CreateQuestionBankQuestionBody,
  ModuleQuizRow,
  ModuleQuizStartResponse,
  ModuleQuizSubmitBody,
  ModuleQuizSubmitResponse,
  PublishQuestionBankBody,
  QuestionBankNameBody,
  QuestionBankQuestion,
  QuestionBankSummary,
  UpdateQuestionBankQuestionBody,
} from './types'

/** Start or resume a module quiz for the signed-in student (idempotent). Pass `{ retake: true }` for a new attempt after submit. */
export async function startModuleQuiz(
  courseId: string,
  moduleId: string,
  body: Record<string, unknown> = {},
): Promise<ModuleQuizStartResponse> {
  return httpPost<ModuleQuizStartResponse>(
    `/courses/${courseId}/modules/${moduleId}/quiz/start`,
    body,
  )
}

export async function submitModuleQuiz(
  courseId: string,
  moduleId: string,
  body: ModuleQuizSubmitBody,
): Promise<ModuleQuizSubmitResponse> {
  return httpPost<ModuleQuizSubmitResponse>(
    `/courses/${courseId}/modules/${moduleId}/quiz/submit`,
    body,
  )
}

export async function listCourseQuestionBanks(courseId: string): Promise<QuestionBankSummary[]> {
  const c = encodeURIComponent(courseId)
  return httpGet<QuestionBankSummary[]>(`/courses/${c}/question-banks`)
}

export async function listCourseModuleQuizzes(courseId: string): Promise<ModuleQuizRow[]> {
  const c = encodeURIComponent(courseId)
  return httpGet<ModuleQuizRow[]>(`/courses/${c}/module-quizzes`)
}

export async function listQuestionBankQuestions(
  courseId: string,
  bankId: string,
): Promise<QuestionBankQuestion[]> {
  const c = encodeURIComponent(courseId)
  const b = encodeURIComponent(bankId)
  return httpGet<QuestionBankQuestion[]>(`/courses/${c}/question-banks/${b}/questions`)
}

export async function createQuestionBank(
  courseId: string,
  body: QuestionBankNameBody,
): Promise<{ questionBankId: string; name: string }> {
  const c = encodeURIComponent(courseId)
  return httpPost<{ questionBankId: string; name: string }>(`/courses/${c}/question-banks`, body)
}

export async function updateQuestionBankName(
  courseId: string,
  bankId: string,
  body: QuestionBankNameBody,
): Promise<{ questionBankId: string; name: string }> {
  const c = encodeURIComponent(courseId)
  const b = encodeURIComponent(bankId)
  return httpPatch<{ questionBankId: string; name: string }>(`/courses/${c}/question-banks/${b}`, body)
}

export async function createQuestionBankQuestion(
  courseId: string,
  bankId: string,
  body: CreateQuestionBankQuestionBody,
): Promise<{ questionId: string }> {
  const c = encodeURIComponent(courseId)
  const b = encodeURIComponent(bankId)
  return httpPost<{ questionId: string }>(`/courses/${c}/question-banks/${b}/questions`, body)
}

export async function updateQuestionBankQuestion(
  courseId: string,
  bankId: string,
  questionId: string,
  body: UpdateQuestionBankQuestionBody,
): Promise<{ status: 'updated' }> {
  const c = encodeURIComponent(courseId)
  const b = encodeURIComponent(bankId)
  const q = encodeURIComponent(questionId)
  return httpPatch<{ status: 'updated' }>(`/courses/${c}/question-banks/${b}/questions/${q}`, body)
}

export async function deleteQuestionBankQuestion(
  courseId: string,
  bankId: string,
  questionId: string,
): Promise<{ status: 'deleted' }> {
  const c = encodeURIComponent(courseId)
  const b = encodeURIComponent(bankId)
  const q = encodeURIComponent(questionId)
  return httpDelete<{ status: 'deleted' }>(`/courses/${c}/question-banks/${b}/questions/${q}`)
}

export async function publishQuestionBank(
  courseId: string,
  bankId: string,
  body: PublishQuestionBankBody,
): Promise<{ status: 'PUBLISHED' }> {
  const c = encodeURIComponent(courseId)
  const b = encodeURIComponent(bankId)
  return httpPost<{ status: 'PUBLISHED' }>(`/courses/${c}/question-banks/${b}/publish`, body)
}

export async function createModuleQuiz(
  courseId: string,
  moduleId: string,
  body: CreateModuleQuizBody,
): Promise<{ quizId: string }> {
  const c = encodeURIComponent(courseId)
  const m = encodeURIComponent(moduleId)
  return httpPost<{ quizId: string }>(`/courses/${c}/modules/${m}/quiz`, body)
}
