import type { CoursePageDocument } from '../course-page'

export type Course = {
  id: string
  title: string
  description: string
  status: 'DRAFT' | 'PUBLISHED'
  createdAt?: string
  updatedAt?: string
  /** Presigned GET URL when the course has a thumbnail; omit if none. */
  thumbnailUrl?: string
  /** True when the viewer may access lessons (purchase or owner/admin). */
  hasAccess?: boolean
  /** Deprecated alias of `hasAccess` for older clients. */
  enrolled?: boolean
  /** One-time price in USD cents when configured (RS-5). */
  amountMinor?: number
  currency?: string
} & Partial<CoursePageDocument>

export type CourseModule = {
  id: string
  title: string
  description: string
  order: number
  createdAt?: string
  updatedAt?: string
  /** True when quiz gating blocks this module for the signed-in student (RS-8). */
  locked?: boolean
  /** Present when the viewer may see that a module quiz exists (enrolled + visibility rules). */
  moduleQuiz?: {
    available: boolean
    servedCountN: number
    latestScorePercent?: number
    passPercent?: number
    passed?: boolean
  }
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

export type ModuleQuizPassOutcome = {
  scorePercent: number
  passPercent: number
  passed: boolean
}

export type ModuleQuizLatestSubmission = {
  correctCount: number
  totalCount: number
  attemptNumber: number
  submittedAt?: string | null
  questions: ModuleQuizResultQuestion[]
} & Partial<ModuleQuizPassOutcome>

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

export type ModuleQuizStartLatestResults = {
  phase: 'latest_results'
  moduleQuizId: string
  moduleId: string
  servedCountN: number
  latestSubmission: ModuleQuizLatestSubmission
} & ModuleQuizPassOutcome

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
} & ModuleQuizPassOutcome

export type ModuleQuizAttemptSummary = {
  attemptId: string
  attemptNumber: number
  correctCount: number
  totalCount: number
  scorePercent: number
  passPercent: number
  passed: boolean
  submittedAt?: string | null
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
  passPercent?: number
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
  /** Lecture notes. Present for viewers who can open the lesson. */
  transcript?: string
}

export type Playback =
  | { provider: 's3'; playbackUrl: string }
  | { provider: 'kinescope'; videoId: string; drmAuthToken: string; watermarkText: string }

export type UserProfile = {
  userId: string
  email: string
  role: string
  cognitoSub: string
  createdAt: string
  updatedAt: string
  givenName?: string
  familyName?: string
  country?: string
  profession?: string
  institution?: string
  researchInterests?: string
  termsAcceptedAt?: string
  privacyAcceptedAt?: string
  autoplayNext?: boolean
  autoMarkComplete?: boolean
  progressCelebrations?: boolean
  researchInterestTags?: string[]
  lastLoginAt?: string
}

export type PatchUserProfileBody = {
  givenName?: string
  familyName?: string
  country?: string
  profession?: string
  institution?: string
  researchInterests?: string
  termsAcceptedAt?: string
  privacyAcceptedAt?: string
  autoplayNext?: boolean
  autoMarkComplete?: boolean
  progressCelebrations?: boolean
  researchInterestTags?: string[]
  resetPreferences?: boolean
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

export type CheckoutProductType = 'course' | 'bundle'

export type CreateCheckoutSessionBody = {
  productType: CheckoutProductType
  courseId?: string
}

export type BundleOffer = {
  amountMinor: number
  currency: string
}

export type PurchaseRecord = {
  id: string
  productType: CheckoutProductType
  status: string
  amountMinor: number
  currency: string
  createdAt: string
  courseId?: string
}

export type PurchasesListResponse = {
  purchases: PurchaseRecord[]
}

export type LessonFileKind = 'resource' | 'download'

export type LessonFileStatus = 'pending' | 'ready'

export type LessonFileListItem = {
  fileId: string
  title: string
  kind: LessonFileKind
  fileType: string
  byteSize: number
  status: LessonFileStatus
  createdAt?: string
}

export type CreateLessonFileResponse = {
  fileId: string
  uploadUrl: string
}

export type CompleteLessonFileResponse = {
  fileId: string
  status: 'ready'
}

export type LessonFileDownloadUrlResponse = {
  url: string
}

export type DeleteLessonFileResponse = {
  fileId: string
  deleted: boolean
}

export type LessonNoteItem = {
  id: string
  courseId: string
  lessonId: string
  body: string
  timestampSec?: number
  createdAt: string
  updatedAt: string
}

export type ListLessonNotesResponse = {
  notes: LessonNoteItem[]
}

export type LessonNoteResponse = {
  note: LessonNoteItem
}

export type DeleteLessonNoteResponse = {
  ok: boolean
}

/** RS-13 assignment narrative: plain text, sanitized rich HTML, or one picture. */
export type AssignmentContentMode = 'plain' | 'rich' | 'image'

export type AssignmentNarrative = {
  mode: AssignmentContentMode
  text?: string
  html?: string
  imageReady?: boolean
}

type AssignmentCriterion = {
  id: string
  label: string
  maxPoints: number
}

type AssignmentMyLatest = {
  id: string
  status: 'draft' | 'submitted' | 'graded'
  scorePercent?: number
  passed?: boolean
  feedback?: string
}

export type Assignment = {
  id: string
  title: string
  moduleId: string
  status: 'draft' | 'published'
  passPercent: number
  countsTowardCertificate: boolean
  locked: boolean
  instructions: AssignmentNarrative
  rubric: AssignmentNarrative
  criteria: AssignmentCriterion[]
  myLatest: AssignmentMyLatest | null
}

export type AssignmentSubmissionFile = {
  id: string
  title: string
  fileType: string
  byteSize: number
  status: 'pending' | 'ready'
}

export type AssignmentSubmissionListItem = {
  id: string
  status: 'draft' | 'submitted' | 'graded'
  note?: string
  scorePercent?: number
  passed?: boolean
  feedback?: string
  files?: AssignmentSubmissionFile[]
}

export type CreateAssignmentSubmissionResponse = {
  id: string
  status: 'draft'
}

export type CreateAssignmentSubmissionFileResponse = {
  fileId: string
  uploadUrl: string
}

export type CompleteAssignmentSubmissionFileResponse = {
  fileId: string
  status: 'ready'
}

export type SubmitAssignmentSubmissionResponse = {
  id: string
  status: 'submitted'
}

export type GradeAssignmentSubmissionResponse = {
  scorePercent: number
  passed: boolean
}

export type AssignmentImageUploadResponse = {
  uploadUrl: string
}

export type AssignmentPresignedUrlResponse = {
  url: string
}

export type CreateAssignmentBody = {
  title: string
  moduleId: string
  passPercent?: number
  countsTowardCertificate?: boolean
}

export type PatchAssignmentBody = {
  title?: string
  moduleId?: string
  passPercent?: number
  countsTowardCertificate?: boolean
  status?: 'draft' | 'published'
  instructions?: {
    mode: AssignmentContentMode
    text?: string
    html?: string
  }
  rubric?: {
    mode: AssignmentContentMode
    text?: string
    html?: string
  }
  criteria?: Array<{ id?: string; label: string; maxPoints: number }>
}

export type GradeAssignmentBody = {
  scores: Array<{ criterionId: string; points: number }>
  feedback: string
}
