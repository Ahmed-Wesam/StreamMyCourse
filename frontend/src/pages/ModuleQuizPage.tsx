import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getCourse, getCourseProgress, listCourseModules, listLessons } from '../lib/api/catalog'
import { isModuleLockedError, isProgressRdsUnavailableError } from '../lib/api/client'
import {
  listModuleQuizAttempts,
  startModuleQuiz,
  submitModuleQuiz,
} from '../lib/api/questionBanks'
import type {
  ModuleQuizAttemptSummary,
  ModuleQuizLatestSubmission,
  ModuleQuizPassOutcome,
  ModuleQuizQuestion,
  ModuleQuizResultQuestion,
  ModuleQuizStartInProgress,
  ModuleQuizStartLatestResults,
  ModuleQuizStartResponse,
  ModuleQuizSubmitResponse,
} from '../lib/api/types'
import {
  courseDetailPath,
  moduleQuizBackLabel,
  resolveModuleQuizBackTo,
  type ModuleQuizReturnTo,
} from '../lib/moduleQuizNavigation'
import {
  catalogApiUserMessage,
  incompleteModuleQuizLinkMessage,
} from '../lib/questionBankErrors'
import { usePageTitle } from '../lib/page-title'
import {
  formatModuleQuizPassThreshold,
  formatModuleQuizQuestionCount,
  moduleQuizPassFailLabel,
} from '../lib/quizScoreDisplay'
import './ModuleQuizPage.css'

type ResultsModel = (ModuleQuizLatestSubmission | ModuleQuizSubmitResponse) & Partial<ModuleQuizPassOutcome>

function mergeLatestResults(data: ModuleQuizStartLatestResults): ResultsModel {
  return {
    ...data.latestSubmission,
    scorePercent: data.scorePercent,
    passPercent: data.passPercent,
    passed: data.passed,
  }
}

function applyStartResponse(
  data: ModuleQuizStartResponse,
  setTaking: (v: ModuleQuizStartInProgress | null) => void,
  setResults: (v: ResultsModel | null) => void,
  setSelected: (v: Record<string, string>) => void,
) {
  if (data.phase === 'latest_results') {
    setTaking(null)
    setResults(mergeLatestResults(data))
    setSelected({})
  } else {
    setTaking(data)
    setResults(null)
    setSelected({})
  }
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="m9 18 6-6-6-6" />
    </svg>
  )
}

function CheckCircleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

export default function ModuleQuizPage() {
  usePageTitle('Quiz')
  const { courseId, moduleId } = useParams<{ courseId: string; moduleId: string }>()
  const location = useLocation()
  const [backTo, setBackTo] = useState<ModuleQuizReturnTo>(() =>
    courseId ? courseDetailPath(courseId) : '/courses',
  )
  const [courseTitle, setCourseTitle] = useState<string>('Course')
  const [moduleTitle, setModuleTitle] = useState<string>('Module')
  const [pageLoading, setPageLoading] = useState(true)
  const [retakeBusy, setRetakeBusy] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [taking, setTaking] = useState<ModuleQuizStartInProgress | null>(null)
  const [results, setResults] = useState<ResultsModel | null>(null)
  const [selectedByQuestionId, setSelectedByQuestionId] = useState<Record<string, string>>({})
  const [passPercentThreshold, setPassPercentThreshold] = useState<number | null>(null)
  const [attemptHistory, setAttemptHistory] = useState<ModuleQuizAttemptSummary[]>([])
  const [attemptHistoryLoading, setAttemptHistoryLoading] = useState(false)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [reviewMode, setReviewMode] = useState(false)
  const [submitModalOpen, setSubmitModalOpen] = useState(false)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const hydrateFromStart = useCallback((data: ModuleQuizStartResponse) => {
    applyStartResponse(data, setTaking, setResults, setSelectedByQuestionId)
    setCurrentQuestionIndex(0)
    setReviewMode(false)
    setSubmitModalOpen(false)
  }, [])

  useEffect(() => {
    if (!courseId || !moduleId) return

    let cancelled = false
    ;(async () => {
      try {
        const [lessons, course] = await Promise.all([
          listLessons(courseId),
          getCourse(courseId).catch(() => null),
        ])
        let progress = null
        try {
          progress = await getCourseProgress(courseId)
        } catch (e) {
          if (!isProgressRdsUnavailableError(e)) throw e
        }
        if (!cancelled) {
          if (course?.title) setCourseTitle(course.title)
          setBackTo(resolveModuleQuizBackTo(courseId, moduleId, location.state?.returnTo, lessons, progress))
        }
      } catch {
        if (!cancelled) setBackTo(courseId ? courseDetailPath(courseId) : '/courses')
      }
    })()

    return () => {
      cancelled = true
    }
  }, [courseId, moduleId, location.state])

  useEffect(() => {
    if (!courseId || !moduleId) {
      setError(incompleteModuleQuizLinkMessage)
      setPageLoading(false)
      return
    }

    let cancelled = false
    setPageLoading(true)
    setError(null)

    void listCourseModules(courseId)
      .then((mods) => {
        if (cancelled) return
        const mod = mods.find((m) => m.id === moduleId)
        if (mod?.title) setModuleTitle(mod.title)
        const threshold = mod?.moduleQuiz?.passPercent
        if (typeof threshold === 'number') setPassPercentThreshold(threshold)
      })
      .catch(() => {
        /* optional metadata */
      })

    startModuleQuiz(courseId, moduleId)
      .then((data) => {
        if (!cancelled) {
          hydrateFromStart(data)
          if (data.phase === 'latest_results') {
            setPassPercentThreshold(data.passPercent)
          }
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(catalogApiUserMessage(e, 'loadModuleQuiz'))
          if (isModuleLockedError(e)) {
            setTaking(null)
            setResults(null)
          }
        }
      })
      .finally(() => {
        if (!cancelled) setPageLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [courseId, moduleId, hydrateFromStart])

  const refreshAttemptHistory = useCallback(() => {
    if (!courseId || !moduleId) return
    setAttemptHistoryLoading(true)
    listModuleQuizAttempts(courseId, moduleId)
      .then((rows) => {
        if (mountedRef.current) setAttemptHistory(rows)
      })
      .catch(() => {
        if (mountedRef.current) setAttemptHistory([])
      })
      .finally(() => {
        if (mountedRef.current) setAttemptHistoryLoading(false)
      })
  }, [courseId, moduleId])

  useEffect(() => {
    if (pageLoading || error || taking !== null) return
    if (results === null) return
    refreshAttemptHistory()
  }, [pageLoading, error, taking, results, refreshAttemptHistory])

  const handleTryAgain = () => {
    if (!courseId || !moduleId) return
    setRetakeBusy(true)
    setError(null)
    startModuleQuiz(courseId, moduleId, { retake: true })
      .then((data) => {
        if (mountedRef.current) hydrateFromStart(data)
      })
      .catch((e: unknown) => {
        if (mountedRef.current) setError(catalogApiUserMessage(e, 'retakeModuleQuiz'))
      })
      .finally(() => {
        if (mountedRef.current) setRetakeBusy(false)
      })
  }

  const handleSelect = (questionId: string, optionKey: string) => {
    setSelectedByQuestionId((prev) => ({ ...prev, [questionId]: optionKey }))
  }

  const handleSubmit = () => {
    if (!courseId || !moduleId || !taking) return
    const { attemptId, questions, servedCountN } = taking
    if (questions.length !== servedCountN) return
    const allKeys = new Set(questions.map((q) => q.id))
    if (allKeys.size !== servedCountN) return
    for (const id of allKeys) {
      if (!selectedByQuestionId[id]) return
    }
    const answers: Record<string, string> = {}
    for (const id of allKeys) {
      answers[id] = selectedByQuestionId[id]!
    }

    setSubmitting(true)
    setError(null)
    setSubmitModalOpen(false)
    submitModuleQuiz(courseId, moduleId, { attemptId, answers })
      .then((res) => {
        if (!mountedRef.current) return
        setTaking(null)
        setResults(res)
        setSelectedByQuestionId({})
        setPassPercentThreshold(res.passPercent)
        setReviewMode(false)
      })
      .catch((e: unknown) => {
        if (mountedRef.current) setError(catalogApiUserMessage(e, 'submitModuleQuiz'))
      })
      .finally(() => {
        if (mountedRef.current) setSubmitting(false)
      })
  }

  const allAnswered =
    taking !== null &&
    taking.questions.length === taking.servedCountN &&
    taking.questions.every((q) => Boolean(selectedByQuestionId[q.id]))

  const showResults = results !== null && taking === null && !pageLoading
  const showTaking = taking !== null && !pageLoading

  const quizLabel = `${moduleTitle} Quiz`

  return (
    <div className="pg-quiz" data-testid="student-page-module-quiz">
      <div className="qz-page">
        <div className="qz-page-header">
          <div className="wrap">
            <div className="qz-breadcrumb">
              <Link to={courseId ? courseDetailPath(courseId) : '/courses'}>{courseTitle}</Link>
              <ChevronRightIcon />
              <span>{moduleTitle}</span>
              <ChevronRightIcon />
              <span style={{ color: 'var(--ink)', fontWeight: 700 }}>{quizLabel}</span>
            </div>
          </div>
        </div>

        {pageLoading && !error && <p className="qz-loading">Loading quiz…</p>}

        {error && !pageLoading && (
          <p className="qz-error" role="alert">
            {error}
          </p>
        )}

        {showTaking && taking && !reviewMode && (
          <QuizTakingInterface
            taking={taking}
            backTo={backTo}
            passPercentThreshold={passPercentThreshold}
            selectedByQuestionId={selectedByQuestionId}
            currentQuestionIndex={currentQuestionIndex}
            onSelect={handleSelect}
            onQuestionIndexChange={setCurrentQuestionIndex}
            onOpenReview={() => setReviewMode(true)}
            allAnswered={allAnswered}
          />
        )}

        {showTaking && taking && reviewMode && (
          <QuizReviewScreen
            taking={taking}
            selectedByQuestionId={selectedByQuestionId}
            allAnswered={allAnswered}
            submitting={submitting}
            onReturn={() => setReviewMode(false)}
            onOpenSubmitModal={() => setSubmitModalOpen(true)}
          />
        )}

        {showResults && results && (
          <QuizResultsScreen
            results={results}
            passPercentThreshold={passPercentThreshold}
            backTo={backTo}
            attemptHistory={attemptHistory}
            attemptHistoryLoading={attemptHistoryLoading}
            retakeBusy={retakeBusy}
            onTryAgain={handleTryAgain}
          />
        )}

        {submitModalOpen && (
          <div
            className="modal-overlay open"
            role="presentation"
            onClick={(e) => {
              if (e.target === e.currentTarget) setSubmitModalOpen(false)
            }}
          >
            <div className="modal-box" role="dialog" aria-labelledby="module-quiz-submit-modal-title">
              <h3 id="module-quiz-submit-modal-title">Submit Quiz?</h3>
              <p>
                Once submitted, your answers will be graded. You can review your results and try again
                with a new question set.
              </p>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  data-testid="module-quiz-submit"
                  disabled={submitting}
                  onClick={handleSubmit}
                >
                  {submitting ? 'Submitting…' : 'Submit answers'}
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSubmitModalOpen(false)}>
                  Go Back
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function QuizTakingInterface({
  taking,
  backTo,
  passPercentThreshold,
  selectedByQuestionId,
  currentQuestionIndex,
  onSelect,
  onQuestionIndexChange,
  onOpenReview,
  allAnswered,
}: {
  taking: ModuleQuizStartInProgress
  backTo: ModuleQuizReturnTo
  passPercentThreshold: number | null
  selectedByQuestionId: Record<string, string>
  currentQuestionIndex: number
  onSelect: (questionId: string, optionKey: string) => void
  onQuestionIndexChange: (index: number) => void
  onOpenReview: () => void
  allAnswered: boolean
}) {
  const total = taking.questions.length
  const safeIndex = Math.min(currentQuestionIndex, Math.max(0, total - 1))
  const question = taking.questions[safeIndex]!
  const answeredCount = taking.questions.filter((q) => selectedByQuestionId[q.id]).length
  const progressPct = total > 0 ? Math.round((answeredCount / total) * 100) : 0
  const submitHelperId = 'module-quiz-submit-helper'

  return (
    <div className="qz-interface-wrap">
      <aside className="qz-sidebar">
        <div className="qz-sidebar-title">Questions</div>
        <div className="qnav-grid">
          {taking.questions.map((q, index) => {
            const answered = Boolean(selectedByQuestionId[q.id])
            const isCurrent = index === safeIndex
            let className = 'qnav-btn'
            if (isCurrent) className += ' current'
            else if (answered) className += ' answered'
            return (
              <button
                key={q.id}
                type="button"
                className={className}
                aria-label={`Question ${index + 1}${answered ? ', answered' : ''}${isCurrent ? ', current' : ''}`}
                aria-current={isCurrent ? 'step' : undefined}
                onClick={() => onQuestionIndexChange(index)}
              >
                {index + 1}
              </button>
            )
          })}
        </div>
        <div className="qnav-legend">
          <h4>Legend</h4>
          <div className="nleg-item">
            <div className="nleg-dot nld-unanswered" />
            Unanswered
          </div>
          <div className="nleg-item">
            <div className="nleg-dot nld-current" />
            Current
          </div>
          <div className="nleg-item">
            <div className="nleg-dot nld-answered" />
            Answered
          </div>
        </div>
        <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--line-2)' }}>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={onOpenReview}
          >
            Review &amp; Submit
          </button>
        </div>
        <p style={{ marginTop: 14, fontSize: 13, fontWeight: 600, color: 'var(--muted)', lineHeight: 1.5 }}>
          {formatModuleQuizQuestionCount(taking.servedCountN)}
          {passPercentThreshold != null ? ` · ${formatModuleQuizPassThreshold(passPercentThreshold)}` : ''}
          {' · '}
          If you leave this page before submitting, your selected answers will be lost.
        </p>
        <Link to={backTo} className="btn btn-ghost btn-sm" style={{ width: '100%', marginTop: 10, justifyContent: 'center' }}>
          {moduleQuizBackLabel(backTo)}
        </Link>
      </aside>

      <div className="qz-main-area">
        <div className="qz-progress">
          <div className="qz-prog-top">
            <span className="qz-prog-label">
              Question {safeIndex + 1} of {total}
            </span>
            <span className="qz-prog-pct">{progressPct}%</span>
          </div>
          <div className="qz-pbar">
            <div className="qz-pbar-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <div className="qz-prog-meta">
            <span className="qz-prog-stat">
              <CheckCircleIcon />
              <span>{answeredCount} answered</span>
            </span>
          </div>
        </div>

        <QuizQuestionCard
          index={safeIndex}
          question={question}
          selectedKey={selectedByQuestionId[question.id]}
          onSelect={(key) => onSelect(question.id, key)}
        />

        <div className="qz-qcard-footer" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={safeIndex === 0}
            onClick={() => onQuestionIndexChange(safeIndex - 1)}
          >
            Previous question
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={safeIndex >= total - 1}
            onClick={() => onQuestionIndexChange(safeIndex + 1)}
          >
            Next question
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={!allAnswered}
            aria-describedby={!allAnswered ? submitHelperId : undefined}
            onClick={onOpenReview}
          >
            Review &amp; Submit
          </button>
          {!allAnswered && (
            <p id={submitHelperId} style={{ width: '100%', fontSize: 13, fontWeight: 600, color: 'var(--muted)' }}>
              Answer every question before submitting.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function QuizQuestionCard({
  index,
  question,
  selectedKey,
  onSelect,
  reviewMode,
}: {
  index: number
  question: ModuleQuizQuestion | ModuleQuizResultQuestion
  selectedKey?: string
  onSelect?: (optionKey: string) => void
  reviewMode?: boolean
}) {
  const options =
    'optionsJson' in question && Array.isArray(question.optionsJson)
      ? question.optionsJson
      : []

  const isResult = 'isCorrect' in question
  const resultQuestion = isResult ? (question as ModuleQuizResultQuestion) : null

  return (
    <fieldset className="qz-qcard">
      <legend className="sr-only">
        Question {index + 1}: {question.promptText}
      </legend>
      <div className="qz-qcard-top">
        <span className="qz-qnum">Question {index + 1}</span>
        <span className="qtype-badge qt-mcq">Multiple choice</span>
      </div>
      <p className="qz-stem">{question.promptText}</p>
      {options.length > 0 ? (
        <div className="qz-options">
          {options.map((option) => {
            const checked = selectedKey === option.key
            let optClass = 'answer-opt'
            if (reviewMode && resultQuestion) {
              if (option.key === resultQuestion.correctOptionKey) optClass += ' correct-ans'
              else if (option.key === resultQuestion.selectedOptionKey && !resultQuestion.isCorrect) {
                optClass += ' wrong-ans'
              } else optClass += ' neutral-ans'
            } else if (checked) {
              optClass += ' selected'
            }
            return (
              <label key={option.key} className={optClass} htmlFor={`${question.id}-${option.key}`}>
                <span className="opt-marker">{option.key}</span>
                <span className="opt-text">{option.text}</span>
                <input
                  id={`${question.id}-${option.key}`}
                  type="radio"
                  name={question.id}
                  value={option.key}
                  checked={checked}
                  disabled={!onSelect}
                  onChange={() => onSelect?.(option.key)}
                  className="sr-only"
                />
              </label>
            )
          })}
        </div>
      ) : (
        isResult &&
        resultQuestion && (
          <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)' }}>
            Your answer: <strong>{resultQuestion.selectedOptionKey}</strong>
            {' · '}
            Correct answer: <strong>{resultQuestion.correctOptionKey}</strong>
            {' · '}
            {resultQuestion.isCorrect ? (
              <strong style={{ color: '#0d6f3e' }}>Correct</strong>
            ) : (
              <strong style={{ color: '#b91c1c' }}>Incorrect</strong>
            )}
          </p>
        )
      )}
    </fieldset>
  )
}

function QuizReviewScreen({
  taking,
  selectedByQuestionId,
  allAnswered,
  submitting,
  onReturn,
  onOpenSubmitModal,
}: {
  taking: ModuleQuizStartInProgress
  selectedByQuestionId: Record<string, string>
  allAnswered: boolean
  submitting: boolean
  onReturn: () => void
  onOpenSubmitModal: () => void
}) {
  const total = taking.questions.length
  const answered = taking.questions.filter((q) => selectedByQuestionId[q.id]).length
  const unanswered = total - answered
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0
  const submitHelperId = 'module-quiz-review-helper'

  return (
    <div className="qz-review-wrap">
      <div className="qz-review-header">
        <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-.02em', marginBottom: 8 }}>
          Ready to Submit?
        </h2>
        <p style={{ fontSize: 15.5, color: 'var(--body)', lineHeight: 1.65, marginBottom: 20 }}>
          Review your progress before submitting. You can still go back and change any answer.
        </p>
        <div className="qz-rev-stats">
          <div className="qz-rev-stat">
            <div className="rsv">{answered}</div>
            <div className="rsl">Answered</div>
          </div>
          <div className="qz-rev-stat">
            <div className="rsv">{unanswered}</div>
            <div className="rsl">Unanswered</div>
          </div>
          <div className="qz-rev-stat">
            <div className="rsv">{pct}%</div>
            <div className="rsl">Answered %</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!allAnswered || submitting}
            aria-describedby={!allAnswered ? submitHelperId : undefined}
            onClick={onOpenSubmitModal}
          >
            Submit answers
          </button>
          <button type="button" className="btn btn-ghost" onClick={onReturn}>
            Return to Quiz
          </button>
        </div>
        {!allAnswered && (
          <p id={submitHelperId} style={{ marginTop: 12, fontSize: 14, fontWeight: 600, color: 'var(--muted)' }}>
            Answer every question before submitting.
          </p>
        )}
      </div>
    </div>
  )
}

function QuizResultsScreen({
  results,
  passPercentThreshold,
  backTo,
  attemptHistory,
  attemptHistoryLoading,
  retakeBusy,
  onTryAgain,
}: {
  results: ResultsModel
  passPercentThreshold: number | null
  backTo: ModuleQuizReturnTo
  attemptHistory: ModuleQuizAttemptSummary[]
  attemptHistoryLoading: boolean
  retakeBusy: boolean
  onTryAgain: () => void
}) {
  const threshold = passPercentThreshold ?? results.passPercent ?? null
  const passed = results.passed === true
  const scorePct = results.scorePercent
  const scoreSummary =
    scorePct != null
      ? `Score ${scorePct}% (${results.correctCount} / ${results.totalCount})`
      : `Score ${results.correctCount} / ${results.totalCount}`

  return (
    <div className="qz-results-wrap">
      <div className="qz-score-card">
        <div style={{ position: 'relative' }}>
          {scorePct != null && <div className="qz-score-big">{scorePct}%</div>}
          <div className="qz-score-fraction">
            {results.correctCount} / {results.totalCount} Correct
          </div>
          {results.passed != null && (
            <div className={`qz-pass-badge ${passed ? 'qzb-pass' : 'qzb-review'}`}>
              <CheckCircleIcon />
              {moduleQuizPassFailLabel(passed)}
              {threshold != null ? ` · ${formatModuleQuizPassThreshold(threshold)}` : ''}
            </div>
          )}
          <p className="qz-pass-msg">
            Attempt {results.attemptNumber} · {scoreSummary} · These are your latest submitted results.
          </p>
        </div>
      </div>

      <div className="qz-ana-card" style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 800, color: 'var(--ink)', marginBottom: 16 }}>Answer review</h3>
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {results.questions.map((q, index) => (
            <li key={q.id}>
              <QuizQuestionCard index={index} question={q} selectedKey={q.selectedOptionKey} reviewMode />
            </li>
          ))}
        </ul>
      </div>

      <ModuleQuizAttemptHistoryList loading={attemptHistoryLoading} attempts={attemptHistory} />

      <div className="qz-bank-note" style={{ marginBottom: 20 }}>
        Trying again draws a new set of questions from the bank and reshuffles them.
      </div>

      <div className="qz-results-actions">
        <button type="button" className="btn btn-ghost" onClick={onTryAgain} disabled={retakeBusy}>
          {retakeBusy ? 'Starting…' : 'Try again'}
        </button>
        <Link to={backTo} className="btn btn-ghost">
          {moduleQuizBackLabel(backTo)}
        </Link>
      </div>
    </div>
  )
}

function ModuleQuizAttemptHistoryList({
  loading,
  attempts,
}: {
  loading: boolean
  attempts: ModuleQuizAttemptSummary[]
}) {
  if (loading && attempts.length === 0) {
    return <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--muted)' }}>Loading attempt history…</p>
  }
  if (attempts.length === 0) return null

  return (
    <div className="qz-ana-card" style={{ marginBottom: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 800, color: 'var(--ink)', marginBottom: 16 }}>Attempt history</h3>
      <div>
        {[...attempts].reverse().map((row) => (
          <div key={row.attemptId} className="qz-attempt-item">
            <span className="qz-att-num">Attempt {row.attemptNumber}</span>
            <span className="qz-att-score">{row.scorePercent}%</span>
            <span className={`qz-att-badge ${row.passed ? 'qzatb-pass' : 'qzatb-fail'}`}>
              {moduleQuizPassFailLabel(row.passed)}
            </span>
            {row.submittedAt ? (
              <span className="qz-att-date">{new Date(row.submittedAt).toLocaleString()}</span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}
