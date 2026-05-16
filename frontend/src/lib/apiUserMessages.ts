import {
  ApiError,
  isLastModuleDeleteError,
  isMediaCleanupUnavailableError,
} from './api'

/** Broken or incomplete URL — question banks list route. */
export const incompleteQuestionBanksListLinkMessage =
  'This link is incomplete. Open Question banks from your course page.'

/** Broken or incomplete URL — question bank studio route. */
export const incompleteQuestionBankStudioLinkMessage =
  'This link is incomplete. Open a question bank from the question banks list.'

/** Broken or incomplete URL — student module quiz route. */
export const incompleteModuleQuizLinkMessage =
  'This link is incomplete. Open the quiz from your course module.'

/** Broken or incomplete URL — lesson player route. */
export const incompleteLessonPlayerLinkMessage =
  'This link is incomplete. Open a lesson from your course.'

export const courseNotFoundMessage =
  'That course was not found or you no longer have access to it.'

type ApiUserMessageContext =
  | 'loadCourses'
  | 'loadCourse'
  | 'createCourse'
  | 'updateCourse'
  | 'deleteCourse'
  | 'publishCourse'
  | 'addLesson'
  | 'deleteLesson'
  | 'createModule'
  | 'deleteModule'
  | 'uploadThumbnail'
  | 'enroll'
  | 'loadLesson'
  | 'loadCatalog'
  | 'loadProfile'
  | 'learnRedirect'

const CONTEXT_FALLBACKS: Record<ApiUserMessageContext, string> = {
  loadCourses: 'Your courses could not be loaded. Please try again.',
  loadCourse: 'This course could not be loaded. Please try again.',
  createCourse: 'The course could not be created. Please try again.',
  updateCourse: 'Your changes could not be saved. Please try again.',
  deleteCourse: 'This course could not be deleted. Please try again.',
  publishCourse: 'This course could not be published. Please try again.',
  addLesson: 'This lesson could not be added. Check the video file and try again.',
  deleteLesson: 'This lesson could not be deleted. Please try again.',
  createModule: 'This module could not be created. Please try again.',
  deleteModule: 'This module could not be deleted. Please try again.',
  uploadThumbnail: 'The thumbnail could not be uploaded. Try another image.',
  enroll: 'Enrollment in this course could not be completed. Please try again.',
  loadLesson: 'This lesson could not be loaded. Please try again.',
  loadCatalog: 'The course catalog could not be loaded. Please try again.',
  loadProfile: 'Your profile could not be loaded. Please try again.',
  learnRedirect: 'Your course could not be opened. Please try again.',
}

const CAMEL_CASE_TOKEN = /\b[a-z]+[A-Z][a-zA-Z]*\b/
const TECHNICAL_TOKEN =
  /\b(questionBankId|moduleId|lessonId|courseId|promptText|optionsJson|correctOptionKey|servedCountN|attemptId|moduleQuizId|quizId|thumbnailKey|cognito_sub|created_by|user_sub|UUID|DRAFT|PUBLISHED|bad_request|not_found|unauthorized|enrollment_required)\b/i
const QUOTED_FIELD_REQUIRED = /'[^']+' is required/i

/** Short or empty API messages that are not useful to show verbatim (e.g. "boom", "Conflict"). */
function isOpaqueMessage(message: string): boolean {
  const trimmed = message.trim()
  if (!trimmed) return true
  if (trimmed.length <= 20 && !/\s{2,}/.test(trimmed) && trimmed.split(/\s+/).length <= 2) {
    return !mapKnownApiMessage(trimmed)
  }
  return false
}

function looksTechnical(message: string): boolean {
  const trimmed = message.trim()
  if (!trimmed) return false
  if (TECHNICAL_TOKEN.test(trimmed)) return true
  if (CAMEL_CASE_TOKEN.test(trimmed)) return true
  if (QUOTED_FIELD_REQUIRED.test(trimmed)) return true
  if (/\bN must\b/i.test(trimmed)) return true
  if (/Cannot publish:\s*N\b/i.test(trimmed)) return true
  if (/Request failed(:\s*\d+)?/i.test(trimmed)) return true
  if (/must be (a |valid )?(json|number|boolean|integer)/i.test(trimmed)) return true
  if (/must not be empty/i.test(trimmed) && /[a-z][A-Z]/.test(trimmed)) return true
  return false
}

function mapKnownApiMessage(message: string): string | null {
  const m = message.trim()
  const lower = m.toLowerCase()

  if (lower.includes('question bank is already linked to another module')) {
    return 'That question bank is already linked to a different module.'
  }
  if (lower.includes('module already has a quiz')) {
    return 'This module already has a quiz attached.'
  }
  if (lower.includes('no module quiz row')) {
    return 'Attach this bank to a module quiz in course management before publishing.'
  }
  if (lower.includes('not in draft status') || lower.includes('cannot accept questions in this status')) {
    return 'This question bank is no longer in draft. Refresh the page to see its current state.'
  }
  if (lower.includes('published questions cannot be updated')) {
    return 'Published questions cannot be edited. Add a new question instead.'
  }
  if (lower.includes('published questions cannot be deleted')) {
    return 'Published questions cannot be deleted.'
  }
  if (lower.includes('no draft questions') || lower.includes('has no draft questions')) {
    return 'Add at least one question before publishing.'
  }
  if (lower.includes('greater than the number of draft questions') || lower.includes('n is greater than')) {
    return 'Choose a question count that is not greater than the number of questions in this bank.'
  }
  if (lower.includes('n must be at least')) {
    return 'Enter at least one question per attempt.'
  }
  if (lower.includes('designated correct answer')) {
    return 'Every question needs a correct answer before you can publish.'
  }
  if (lower.includes('prompttext') || lower.includes('prompt must') || lower.includes('prompt text')) {
    return 'Enter the question text.'
  }
  if (lower.includes('optionsjson') || lower.includes('options json') || lower.includes('at least two')) {
    return 'Add at least two answer choices with text for each question.'
  }
  if (lower.includes('correctoptionkey') || lower.includes('correct option key')) {
    return 'Choose the correct answer for this question.'
  }
  if (lower.includes('questionbankid') || lower.includes('question bank id')) {
    return 'Choose a question bank to attach.'
  }
  if (lower.includes('module quiz not available')) {
    return 'This quiz is not available. It may not be published yet, or you may not have access.'
  }
  if (lower.includes('attempt not found') || lower.includes('attempt already submitted')) {
    return 'This quiz attempt is no longer active. Refresh the page and try again.'
  }
  if (lower.includes('answers incomplete') || lower.includes('answer every question')) {
    return 'Answer every question before submitting.'
  }
  if (lower.includes('invalid payload')) {
    return 'Your answers could not be submitted. Refresh the page and try again.'
  }
  if (lower.includes('stale attempt') || lower.includes('does not match')) {
    return 'This attempt is out of date. Refresh the page and try again.'
  }
  if (lower.includes('cannot start retake')) {
    return 'You cannot start a new attempt right now. Refresh the page and try again.'
  }
  if (lower.includes('name must not be empty')) {
    return 'Enter a question bank name.'
  }
  if (
    lower.includes('name must be at most') ||
    (lower.includes('name must be ') && lower.includes('characters or fewer'))
  ) {
    return 'Question bank name is too long.'
  }
  if (lower === 'conflict') {
    return 'This action conflicts with the current state. Refresh the page and try again.'
  }

  if (lower.includes('cannot delete the last module')) {
    return "You can't delete the last module — every course needs at least one section."
  }
  if (lower.includes('media cleanup')) {
    return "Media cleanup is not configured for this environment, so modules with uploaded videos can't be deleted right now. Contact an admin."
  }
  if (lower.includes('course needs at least one ready lesson')) {
    return 'Add at least one lesson with a ready video before you can publish this course.'
  }
  if (lower.includes('no video uploaded') || lower.includes('no video uploaded for lesson')) {
    return 'Upload a video for this lesson first.'
  }
  if (lower.includes('video not ready')) {
    return "This lesson's video is still processing. Try again in a few minutes."
  }
  if (lower.includes('invalid thumbnail')) {
    return 'That image could not be used. Try another file.'
  }
  if (lower.includes('enrollment required') || lower.includes('not enrolled')) {
    return 'Enroll in this course to access this content.'
  }
  if (lower.includes('authentication required') || lower === 'unauthorized' || lower.includes('sign in')) {
    return 'Sign in to continue.'
  }
  if (lower === 'course not found' || lower.includes('course not found')) {
    return 'That course was not found or you no longer have access to it.'
  }
  if (lower === 'lesson not found' || lower.includes('lesson not found')) {
    return 'That lesson was not found. Refresh the page and try again.'
  }
  if (lower === 'module not found' || lower.includes('module not found')) {
    return 'That module was not found. Refresh the page and try again.'
  }
  if (lower === 'not found') {
    return 'That item was not found or you no longer have access to it.'
  }

  return null
}

function fallbackForContext(context?: ApiUserMessageContext): string {
  if (context && CONTEXT_FALLBACKS[context]) return CONTEXT_FALLBACKS[context]
  return 'Something went wrong. Please try again.'
}

function readApiError(err: unknown): ApiError | null {
  if (
    typeof err === 'object' &&
    err !== null &&
    (err as ApiError).name === 'ApiError' &&
    typeof (err as ApiError).status === 'number' &&
    typeof (err as ApiError).message === 'string'
  ) {
    return err as ApiError
  }
  return null
}

function mapByApiErrorCode(err: ApiError): string | null {
  if (isLastModuleDeleteError(err)) {
    return "You can't delete the last module — every course needs at least one section."
  }
  if (isMediaCleanupUnavailableError(err)) {
    return "Media cleanup is not configured for this environment, so modules with uploaded videos can't be deleted right now. Contact an admin."
  }
  return null
}

/**
 * User-facing copy for catalog API failures and related errors.
 */
export function catalogApiUserMessage(err: unknown, context?: ApiUserMessageContext): string {
  const apiErr = readApiError(err)
  if (apiErr) {
    const byCode = mapByApiErrorCode(apiErr)
    if (byCode) return byCode

    const mapped = mapKnownApiMessage(apiErr.message)
    if (mapped) return mapped

    if (apiErr.status === 404) {
      return 'That item was not found or you no longer have access to it.'
    }
    if (apiErr.status === 409) {
      return 'This action conflicts with the current state. Refresh the page and try again.'
    }
    if (apiErr.status === 400) {
      return context
        ? fallbackForContext(context)
        : 'That request could not be completed. Check your entries and try again.'
    }
    if (apiErr.status === 401 || apiErr.status === 403) {
      if (apiErr.message.trim() && !looksTechnical(apiErr.message)) {
        const known = mapKnownApiMessage(apiErr.message)
        if (known) return known
      }
      return apiErr.status === 401 ? 'Sign in to continue.' : 'You do not have permission to do that.'
    }
    if (apiErr.message.trim() && !looksTechnical(apiErr.message) && !isOpaqueMessage(apiErr.message)) {
      return apiErr.message.trim()
    }
    return fallbackForContext(context)
  }

  if (err instanceof Error) {
    const trimmed = err.message.trim()
    if (trimmed && !looksTechnical(trimmed)) {
      const known = mapKnownApiMessage(trimmed)
      if (known) return known
      if (context) return fallbackForContext(context)
      return trimmed
    }
  }

  return fallbackForContext(context)
}

/** @deprecated Use {@link catalogApiUserMessage} — kept for question-bank call sites. */
export function questionBankUserMessage(err: unknown, context?: ApiUserMessageContext): string {
  return catalogApiUserMessage(err, context)
}

/** User-visible message for failed module delete, or null to use generic fallback. */
export function moduleDeleteFailureMessage(err: unknown): string | null {
  const apiErr = readApiError(err)
  if (!apiErr) return null
  return mapByApiErrorCode(apiErr)
}
