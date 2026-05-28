export type Course = {
  id: string
  title: string
  description: string
  status: 'DRAFT' | 'PUBLISHED'
  createdAt?: string
  updatedAt?: string
  /** Presigned GET URL when the course has a thumbnail; omit if none. */
  thumbnailUrl?: string
  /** True when the viewer may access lessons (subscription or owner/admin). */
  hasAccess?: boolean
  /** Deprecated alias of `hasAccess` for older clients. */
  enrolled?: boolean
}

export type CourseModule = {
  id: string
  title: string
  description: string
  order: number
  createdAt?: string
  updatedAt?: string
  /** Present when the viewer may see that a module quiz exists (enrolled + visibility rules). */
  moduleQuiz?: { available: boolean; servedCountN: number; latestScorePercent?: number }
}

type ModuleQuizOption = {
  key: string
  text: string
}

export type ModuleQuizQuestion = {
  id: string
  promptText: string
  optionsJson: ModuleQuizOption[]
}

/** Per-question scored row (submit 200 or latest submission breakdown). */
export type ModuleQuizResultQuestion = {
  id: string
  promptText: string
  selectedOptionKey: string
  correctOptionKey: string
  isCorrect: boolean
}

export type ModuleQuizLatestSubmission = {
  correctCount: number
  totalCount: number
  attemptNumber: number
  submittedAt?: string | null
  questions: ModuleQuizResultQuestion[]
}

export type ModuleQuizStartInProgress = {
  phase: 'in_progress'
  moduleQuizId: string
  moduleId: string
  servedCountN: number
  attemptId: string
  attemptNumber: number
  /** Display order; matches `questions[].id` order. */
  questionIds: string[]
  questions: ModuleQuizQuestion[]
}

type ModuleQuizStartLatestResults = {
  phase: 'latest_results'
  moduleQuizId: string
  moduleId: string
  servedCountN: number
  latestSubmission: ModuleQuizLatestSubmission
}

export type ModuleQuizStartResponse = ModuleQuizStartInProgress | ModuleQuizStartLatestResults

export type ModuleQuizSubmitBody = {
  attemptId: string
  answers: Record<string, string>
}

export type ModuleQuizSubmitResponse = {
  attemptId: string
  attemptNumber: number
  correctCount: number
  totalCount: number
  questions: ModuleQuizResultQuestion[]
}

export type QuestionBankStatus = 'DRAFT' | 'PUBLISHED'

export type QuestionBankSummary = {
  questionBankId: string
  /** Human label for instructors. Older API rows may omit it, so UI should keep an id fallback. */
  name?: string | null
  status: QuestionBankStatus
  createdAt?: string
  updatedAt?: string
}

/** One `module_quizzes` row for publisher list (modules without a quiz are omitted). */
export type ModuleQuizRow = {
  quizId: string
  moduleId: string
  questionBankId: string | null
  servedCountN: number | null
  createdAt?: string
  updatedAt?: string
}

export type QuestionBankQuestion = {
  questionId: string
  status: QuestionBankStatus
  promptText: string
  optionsJson: ModuleQuizOption[]
  correctOptionKey?: string | null
}

export type CreateQuestionBankQuestionBody = {
  promptText: string
  optionsJson: ModuleQuizOption[]
  /** Must match a key in `optionsJson` when set; required when appending to a PUBLISHED bank. */
  correctOptionKey?: string
}

/**
 * PATCH body for a **DRAFT** MCQ only. The server requires **at least one** of these fields per request.
 */
export type UpdateQuestionBankQuestionBody = Partial<
  Pick<CreateQuestionBankQuestionBody, 'promptText' | 'optionsJson' | 'correctOptionKey'>
>

export type PublishQuestionBankBody = {
  n: number
  moduleId: string
}

export type CreateModuleQuizBody = {
  questionBankId: string
}

export type QuestionBankNameBody = {
  name: string
}

export type Lesson = {
  id: string
  title: string
  order: number
  moduleId: string
  /** Display order of the parent module within the course */
  moduleOrder: number
  videoStatus: 'pending' | 'ready'
  duration?: number
  /** Presigned GET when a lesson thumbnail exists. */
  thumbnailUrl?: string
}

export type Playback =
  | { provider: 's3'; playbackUrl: string }
  | { provider: 'kinescope'; videoId: string; drmAuthToken: string }

export type UserProfile = {
  userId: string
  email: string
  role: string
  cognitoSub: string
  createdAt: string
  updatedAt: string
}

export type LessonProgressItem = {
  lessonId: string
  completed: boolean
  completedAt?: string
  lastPositionSec: number
}

export type CourseProgress = {
  courseId: string
  totalReadyLessons: number
  completedCount: number
  percentComplete: number
  lessons: LessonProgressItem[]
}

export type UpdateLessonProgressBody = {
  lastPositionSec: number
  /** Total lesson length in seconds (from `Lesson.duration` or `HTMLVideoElement.duration`); sent to the API as `duration`. */
  durationSec: number
  markComplete?: boolean
  markIncomplete?: boolean
}

export type UpdateProgressResponse = {
  ok: true
  lessonProgress?: LessonProgressItem
}

export type CheckoutSessionResponse = {
  redirect_url: string
}

/** Manage-contract-v1 read model for GET /billing/subscription. */
export type SubscriptionSummary = {
  status: 'active' | 'past_due' | 'canceled'
  currentPeriodEnd: string
  cancelAtPeriodEnd: boolean
  canCancel: boolean
  nextBillingDate: string | null
  amountMinor: number
  currency: string
  planLabel: string
  pastDue: boolean
}

export type CancelSubscriptionResponse = {
  status: string
  cancelAtPeriodEnd: boolean
  currentPeriodEnd: string
}
