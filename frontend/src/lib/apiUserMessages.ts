import {
  ApiError,
  isAlreadyCanceledError,
  isAlreadySubscribedError,
  isCannotCancelError,
  isCheckoutInProgressError,
  isBillingUnconfiguredError,
  isLastModuleDeleteError,
  isMediaCleanupUnavailableError,
  isNotSubscribedError,
  isProviderAgreementMissingError,
  isProviderCancelFailedError,
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
  | 'subscribe'
  | 'loadSubscription'
  | 'cancelSubscription'
  | 'loadLesson'
  | 'loadProfile'
  | 'learnRedirect'
  | 'loadModuleQuiz'
  | 'submitModuleQuiz'
  | 'retakeModuleQuiz'
  | 'loadQuestionBanks'
  | 'createQuestionBank'
  | 'loadQuestionBank'
  | 'saveQuestionBank'
  | 'saveQuestionBankQuestion'
  | 'deleteQuestionBankQuestion'
  | 'publishQuestionBank'
  | 'attachModuleQuiz'

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
  subscribe: 'Checkout could not be started. Please try again.',
  loadSubscription: 'Your subscription could not be loaded. Please try again.',
  cancelSubscription: 'Your subscription could not be canceled. Please try again.',
  loadLesson: 'This lesson could not be loaded. Please try again.',
  loadProfile: 'Your profile could not be loaded. Please try again.',
  learnRedirect: 'Your course could not be opened. Please try again.',
  loadModuleQuiz: 'This quiz could not be loaded. Refresh the page and try again.',
  submitModuleQuiz: 'Your answers could not be submitted. Refresh the page and try again.',
  retakeModuleQuiz: 'A new quiz attempt could not be started. Refresh the page and try again.',
  loadQuestionBanks: 'Question banks could not be loaded. Please try again.',
  createQuestionBank: 'The question bank could not be created. Please try again.',
  loadQuestionBank: 'This question bank could not be loaded. Please try again.',
  saveQuestionBank: 'The question bank could not be saved. Please try again.',
  saveQuestionBankQuestion: 'That question could not be saved. Please try again.',
  deleteQuestionBankQuestion: 'That question could not be deleted. Please try again.',
  publishQuestionBank: 'This question bank could not be published. Please try again.',
  attachModuleQuiz: 'The module quiz could not be attached. Please try again.',
}

const CAMEL_CASE_TOKEN = /\b[a-z]+[A-Z][a-zA-Z]*\b/
const TECHNICAL_TOKEN =
  /\b(questionBankId|moduleId|lessonId|courseId|promptText|optionsJson|correctOptionKey|servedCountN|attemptId|moduleQuizId|quizId|thumbnailKey|cognito_sub|created_by|user_sub|UUID|DRAFT|PUBLISHED|bad_request|not_found|unauthorized|enrollment_required)\b/i
const QUOTED_FIELD_REQUIRED = /'[^']+' is required/i

type MessageRule = {
  test: (lower: string) => boolean
  message: string
}

const KNOWN_MESSAGE_RULES: MessageRule[] = [
  {
    test: (l) => l.includes('question bank is already linked to another module'),
    message: 'That question bank is already linked to a different module.',
  },
  {
    test: (l) => l.includes('module already has a quiz'),
    message: 'This module already has a quiz attached.',
  },
  {
    test: (l) => l.includes('no module quiz row'),
    message: 'Attach this bank to a module quiz in course management before publishing.',
  },
  {
    test: (l) => l.includes('not in draft status') || l.includes('cannot accept questions in this status'),
    message: 'This question bank is no longer in draft. Refresh the page to see its current state.',
  },
  {
    test: (l) => l.includes('published questions cannot be updated'),
    message: 'Published questions cannot be edited. Add a new question instead.',
  },
  {
    test: (l) => l.includes('published questions cannot be deleted'),
    message: 'Published questions cannot be deleted.',
  },
  {
    test: (l) => l.includes('no draft questions') || l.includes('has no draft questions'),
    message: 'Add at least one question before publishing.',
  },
  {
    test: (l) => l.includes('greater than the number of draft questions') || l.includes('n is greater than'),
    message: 'Choose a question count that is not greater than the number of questions in this bank.',
  },
  {
    test: (l) => l.includes('n must be at least'),
    message: 'Enter at least one question per attempt.',
  },
  {
    test: (l) => l.includes('designated correct answer'),
    message: 'Every question needs a correct answer before you can publish.',
  },
  {
    test: (l) => l.includes('prompttext') || l.includes('prompt must') || l.includes('prompt text'),
    message: 'Enter the question text.',
  },
  {
    test: (l) => l.includes('duplicate option key'),
    message: 'Each answer choice needs a unique label (for example A, B, C).',
  },
  {
    test: (l) => l.includes('optionsjson') || l.includes('options json'),
    message: 'Add at least two answer choices with text for each question.',
  },
  {
    test: (l) => l.includes('correctoptionkey') || l.includes('correct option key'),
    message: 'Choose the correct answer for this question.',
  },
  {
    test: (l) => l.includes('questionbankid') || l.includes('question bank id'),
    message: 'Choose a question bank to attach.',
  },
  {
    test: (l) => l.includes('module quiz not available'),
    message: 'This quiz is not available. It may not be published yet, or you may not have access.',
  },
  {
    test: (l) => l.includes('module quiz questions could not be loaded'),
    message: 'This quiz could not be loaded. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('module quiz binding'),
    message: 'This quiz could not be loaded. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('module quiz submission is incomplete'),
    message: 'Your answers could not be submitted. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('attempt not found') || l.includes('attempt already submitted'),
    message: 'This quiz attempt is no longer active. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('answers incomplete') || l.includes('answer every question'),
    message: 'Answer every question before submitting.',
  },
  {
    test: (l) => l.includes('invalid payload'),
    message: 'Your answers could not be submitted. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('stale attempt') || l.includes('does not match current question set'),
    message: 'This attempt is out of date. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('cannot start retake'),
    message: 'You cannot start a new attempt right now. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('name must not be empty'),
    message: 'Enter a question bank name.',
  },
  {
    test: (l) =>
      l.includes('name must be at most') || (l.includes('name must be ') && l.includes('characters or fewer')),
    message: 'Question bank name is too long.',
  },
  {
    test: (l) => l === 'conflict',
    message: 'This action conflicts with the current state. Refresh the page and try again.',
  },
  {
    test: (l) => l.includes('cannot delete the last module'),
    message: "You can't delete the last module — every course needs at least one section.",
  },
  {
    test: (l) => l.includes('media cleanup'),
    message:
      "Media cleanup is not configured for this environment, so modules with uploaded videos can't be deleted right now. Contact an admin.",
  },
  {
    test: (l) => l.includes('course needs at least one ready lesson'),
    message: 'Add at least one lesson with a ready video before you can publish this course.',
  },
  {
    test: (l) => l.includes('no video uploaded') || l.includes('no video uploaded for lesson'),
    message: 'Upload a video for this lesson first.',
  },
  {
    test: (l) => l.includes('video not ready'),
    message: "This lesson's video is still processing. Try again in a few minutes.",
  },
  {
    test: (l) => l.includes('invalid thumbnail'),
    message: 'That image could not be used. Try another file.',
  },
  {
    test: (l) => l.includes('enrollment required') || l.includes('not enrolled'),
    message: 'Enroll in this course to access this content.',
  },
  {
    test: (l) => l.includes('authentication required') || l === 'unauthorized' || l.includes('sign in'),
    message: 'Sign in to continue.',
  },
  {
    test: (l) => l === 'course not found' || l.includes('course not found'),
    message: courseNotFoundMessage,
  },
  {
    test: (l) => l === 'lesson not found' || l.includes('lesson not found'),
    message: 'That lesson was not found. Refresh the page and try again.',
  },
  {
    test: (l) => l === 'module not found' || l.includes('module not found'),
    message: 'That module was not found. Refresh the page and try again.',
  },
  {
    test: (l) => l === 'not found',
    message: 'That item was not found or you no longer have access to it.',
  },
]

function mapKnownApiMessage(message: string): string | null {
  const lower = message.trim().toLowerCase()
  if (!lower) return null
  for (const rule of KNOWN_MESSAGE_RULES) {
    if (rule.test(lower)) return rule.message
  }
  return null
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
  if (isBillingUnconfiguredError(err)) {
    return 'Subscriptions are not available right now. Please try again later.'
  }
  if (isAlreadySubscribedError(err)) {
    return 'You already have an active subscription.'
  }
  if (isCheckoutInProgressError(err)) {
    return 'A checkout is already in progress. Wait a moment or try again shortly.'
  }
  if (isNotSubscribedError(err)) {
    return 'You do not have a subscription to manage yet.'
  }
  if (isAlreadyCanceledError(err)) {
    return 'Your subscription is already set to cancel at the end of the billing period.'
  }
  if (isCannotCancelError(err)) {
    return 'Your subscription cannot be canceled in its current state.'
  }
  if (isProviderCancelFailedError(err)) {
    return 'Your cancellation was saved, but we could not stop renewal with the payment provider. Try again using the button below.'
  }
  if (isProviderAgreementMissingError(err)) {
    return 'Your cancellation was saved, but we could not find a payment agreement to stop renewal. Please contact support.'
  }
  if (isLastModuleDeleteError(err)) {
    return "You can't delete the last module — every course needs at least one section."
  }
  if (isMediaCleanupUnavailableError(err)) {
    return "Media cleanup is not configured for this environment, so modules with uploaded videos can't be deleted right now. Contact an admin."
  }
  return null
}

function messageFromApiError(apiErr: ApiError, context?: ApiUserMessageContext): string {
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
    return apiErr.status === 401 ? 'Sign in to continue.' : 'You do not have permission to do that.'
  }

  return fallbackForContext(context)
}

/**
 * User-facing copy for catalog API failures and related errors.
 */
export function catalogApiUserMessage(err: unknown, context?: ApiUserMessageContext): string {
  const apiErr = readApiError(err)
  if (apiErr) {
    return messageFromApiError(apiErr, context)
  }

  if (err instanceof Error) {
    const trimmed = err.message.trim()
    if (trimmed && !looksTechnical(trimmed)) {
      const known = mapKnownApiMessage(trimmed)
      if (known) return known
    }
    return fallbackForContext(context)
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
