import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { SectionHeader } from '../components/ui/SectionHeader'
import { getCourseProgress, listCourseModules, listLessons } from '../lib/api/catalog'
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
  moduleQuizPassFailLabel,
  quizScorePercentPillClass,
} from '../lib/quizScoreDisplay'

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

export default function ModuleQuizPage() {
  usePageTitle('Quiz')
  const { courseId, moduleId } = useParams<{ courseId: string; moduleId: string }>()
  const location = useLocation()
  const [backTo, setBackTo] = useState<ModuleQuizReturnTo>(() =>
    courseId ? courseDetailPath(courseId) : '/courses',
  )
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
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const hydrateFromStart = useCallback((data: ModuleQuizStartResponse) => {
    applyStartResponse(data, setTaking, setResults, setSelectedByQuestionId)
  }, [])

  useEffect(() => {
    if (!courseId || !moduleId) return

    let cancelled = false
    ;(async () => {
      try {
        const lessons = await listLessons(courseId)
        let progress = null
        try {
          progress = await getCourseProgress(courseId)
        } catch (e) {
          if (!isProgressRdsUnavailableError(e)) throw e
        }
        if (!cancelled) {
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
    submitModuleQuiz(courseId, moduleId, { attemptId, answers })
      .then((res) => {
        if (!mountedRef.current) return
        setTaking(null)
        setResults(res)
        setSelectedByQuestionId({})
        setPassPercentThreshold(res.passPercent)
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

  return (
    <div className="space-y-8 py-6 text-rs-ink sm:py-8">
      <Card className="overflow-hidden shadow-rs-sm">
        <ModuleQuizCardHeader
          backTo={backTo}
          taking={taking}
          results={results}
          passPercentThreshold={passPercentThreshold}
        />

        <ModuleQuizCardMain
          pageLoading={pageLoading}
          error={error}
          taking={taking}
          results={results}
          passPercentThreshold={passPercentThreshold}
          attemptHistory={attemptHistory}
          attemptHistoryLoading={attemptHistoryLoading}
          selectedByQuestionId={selectedByQuestionId}
          allAnswered={allAnswered}
          submitting={submitting}
          retakeBusy={retakeBusy}
          onSelect={handleSelect}
          onSubmit={handleSubmit}
          onTryAgain={handleTryAgain}
        />
      </Card>
    </div>
  )
}

function ModuleQuizCardHeader({
  backTo,
  taking,
  results,
  passPercentThreshold,
}: {
  backTo: ModuleQuizReturnTo
  taking: ModuleQuizStartInProgress | null
  results: ResultsModel | null
  passPercentThreshold: number | null
}) {
  const showTaking = taking !== null
  const showResults = results !== null && taking === null
  const threshold =
    passPercentThreshold ??
    (showResults && results?.passPercent != null ? results.passPercent : null)

  let lead: string | undefined
  if (showTaking && taking) {
    const passHint =
      threshold != null ? ` · ${formatModuleQuizPassThreshold(threshold)}` : ''
    lead = `${taking.questions.length} of ${taking.servedCountN} questions${passHint} · If you leave this page before submitting, your selected answers will be lost.`
  } else if (showResults && results) {
    const scoreLine =
      results.scorePercent != null
        ? `Score ${results.scorePercent}% (${results.correctCount} / ${results.totalCount})`
        : `Score ${results.correctCount} / ${results.totalCount}`
    const passLine =
      threshold != null ? ` · ${formatModuleQuizPassThreshold(threshold)}` : ''
    lead = `Attempt ${results.attemptNumber} · ${scoreLine}${passLine} · These are your latest submitted results.`
  }

  return (
    <div className="border-b border-rs-line bg-rs-grad-soft px-6 py-5 sm:px-8 sm:py-6">
      <Link
        to={backTo}
        className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-rs-muted no-underline transition-colors hover:text-rs-navy"
      >
        <svg className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        {moduleQuizBackLabel(backTo)}
      </Link>
      <SectionHeader
        kicker="Knowledge check"
        title="Module quiz"
        lead={lead}
        align="start"
        level={2}
      />
    </div>
  )
}

function ModuleQuizCardMain({
  pageLoading,
  error,
  taking,
  results,
  passPercentThreshold,
  attemptHistory,
  attemptHistoryLoading,
  selectedByQuestionId,
  allAnswered,
  submitting,
  retakeBusy,
  onSelect,
  onSubmit,
  onTryAgain,
}: {
  pageLoading: boolean
  error: string | null
  taking: ModuleQuizStartInProgress | null
  results: ResultsModel | null
  passPercentThreshold: number | null
  attemptHistory: ModuleQuizAttemptSummary[]
  attemptHistoryLoading: boolean
  selectedByQuestionId: Record<string, string>
  allAnswered: boolean
  submitting: boolean
  retakeBusy: boolean
  onSelect: (questionId: string, optionKey: string) => void
  onSubmit: () => void
  onTryAgain: () => void
}) {
  const showResults = results !== null && taking === null
  const showTaking = taking !== null && !error
  const submitHelperId = 'module-quiz-submit-helper'
  const blockQuestions = Boolean(error)

  return (
    <>
      {pageLoading && (
        <div className="px-6 py-12 text-center text-sm font-semibold text-rs-muted sm:px-8">Loading quiz…</div>
      )}

      {error && !pageLoading && (
        <div className="mx-6 my-6 rounded-rs-sm border border-red-200 bg-red-50 p-4 sm:mx-8">
          <p className="text-sm font-semibold text-red-700">{error}</p>
        </div>
      )}

      {!pageLoading && !blockQuestions && showTaking && taking && (
        <>
          <div className="divide-y divide-rs-line">
            {taking.questions.map((question, index) => (
              <QuizQuestionBlock
                key={question.id}
                index={index}
                question={question}
                selectedKey={selectedByQuestionId[question.id]}
                onSelect={(key) => onSelect(question.id, key)}
              />
            ))}
          </div>
          <div className="border-t border-rs-line bg-rs-sky-2/50 px-6 py-5 sm:px-8">
            <Button
              type="button"
              onClick={onSubmit}
              disabled={!allAnswered || submitting}
              aria-describedby={!allAnswered ? submitHelperId : undefined}
              className="disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? 'Submitting…' : 'Submit answers'}
            </Button>
            {!allAnswered && (
              <p id={submitHelperId} className="mt-3 text-sm font-semibold text-rs-muted">
                Answer every question before submitting.
              </p>
            )}
          </div>
        </>
      )}

      {!pageLoading && !blockQuestions && showResults && results && (
        <div className="space-y-6 px-6 py-6 sm:px-8 sm:py-8">
          <QuizPassOutcomeBanner results={results} passPercentThreshold={passPercentThreshold} />
          <QuizResultsBreakdown questions={results.questions} />
          <ModuleQuizAttemptHistoryList loading={attemptHistoryLoading} attempts={attemptHistory} />
          <div className="space-y-3 rounded-rs-sm border border-rs-line bg-rs-sky-2/40 p-5">
            <p className="text-sm font-semibold text-rs-body">
              Trying again draws a new set of questions from the bank and reshuffles them.
            </p>
            <Button type="button" variant="ghost" onClick={onTryAgain} disabled={retakeBusy}>
              {retakeBusy ? 'Starting…' : 'Try again'}
            </Button>
          </div>
        </div>
      )}
    </>
  )
}

function QuizPassOutcomeBanner({
  results,
  passPercentThreshold,
}: {
  results: ResultsModel
  passPercentThreshold: number | null
}) {
  if (results.passed == null && results.scorePercent == null) return null
  const threshold = passPercentThreshold ?? results.passPercent ?? null
  const passed = results.passed === true
  return (
    <div
      className={`rounded-rs-sm border px-5 py-4 ${
        passed ? 'border-emerald-200/80 bg-emerald-50/70' : 'border-amber-200/80 bg-amber-50/70'
      }`}
    >
      <div className="flex flex-wrap items-center gap-3">
        {results.scorePercent != null ? (
          <span className={`${quizScorePercentPillClass(results.scorePercent)} text-sm`}>
            {results.scorePercent}%
          </span>
        ) : null}
        <p className="text-sm font-extrabold text-rs-ink">
          {moduleQuizPassFailLabel(passed)}
          {threshold != null ? ` · ${formatModuleQuizPassThreshold(threshold)}` : ''}
        </p>
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
    return (
      <p className="text-sm font-semibold text-rs-muted">Loading attempt history…</p>
    )
  }
  if (attempts.length === 0) return null

  return (
    <div className="rounded-rs-sm border border-rs-line bg-white p-5">
      <h3 className="text-sm font-extrabold text-rs-navy">Attempt history</h3>
      <ul className="mt-3 space-y-2">
        {[...attempts].reverse().map((row) => (
          <li
            key={row.attemptId}
            className="flex flex-wrap items-center justify-between gap-2 rounded-rs-sm border border-rs-line/80 bg-rs-sky-2/30 px-3 py-2 text-sm"
          >
            <span className="font-semibold text-rs-ink">Attempt {row.attemptNumber}</span>
            <span className={`${quizScorePercentPillClass(row.scorePercent)}`}>{row.scorePercent}%</span>
            <span
              className={`font-bold ${row.passed ? 'text-emerald-800' : 'text-amber-900'}`}
            >
              {moduleQuizPassFailLabel(row.passed)}
            </span>
            {row.submittedAt ? (
              <span className="w-full text-xs font-semibold text-rs-muted sm:w-auto sm:ml-auto">
                {new Date(row.submittedAt).toLocaleString()}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

function QuizResultsBreakdown({ questions }: { questions: ModuleQuizResultQuestion[] }) {
  return (
    <ul className="space-y-4">
      {questions.map((q, index) => (
        <li
          key={q.id}
          className={`rounded-rs-sm border px-4 py-4 sm:px-5 ${
            q.isCorrect
              ? 'border-emerald-200/80 bg-emerald-50/70'
              : 'border-amber-200/80 bg-amber-50/70'
          }`}
        >
          <p className="text-sm font-extrabold text-rs-ink">
            <span className="mr-2 text-xs font-bold uppercase tracking-wide text-rs-muted">
              Question {index + 1}
            </span>
            {q.promptText}
          </p>
          <p className="mt-2 text-sm font-semibold text-rs-body">
            Your answer: <span className="font-extrabold text-rs-ink">{q.selectedOptionKey}</span>
            {' · '}
            Correct answer: <span className="font-extrabold text-rs-ink">{q.correctOptionKey}</span>
            {' · '}
            {q.isCorrect ? (
              <span className="font-extrabold text-emerald-800">Correct</span>
            ) : (
              <span className="font-extrabold text-amber-900">Incorrect</span>
            )}
          </p>
        </li>
      ))}
    </ul>
  )
}

function QuizQuestionBlock({
  index,
  question,
  selectedKey,
  onSelect,
}: {
  index: number
  question: ModuleQuizQuestion
  selectedKey?: string
  onSelect: (optionKey: string) => void
}) {
  const options = Array.isArray(question.optionsJson) ? question.optionsJson : []

  return (
    <fieldset className="px-6 py-6 sm:px-8 sm:py-7">
      <legend className="mb-4 text-base font-extrabold leading-snug text-rs-navy">
        <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-rs-muted">
          Question {index + 1}
        </span>
        {question.promptText}
      </legend>
      <div className="space-y-2.5">
        {options.map((option) => {
          const inputId = `${question.id}-${option.key}`
          const checked = selectedKey === option.key
          return (
            <label
              key={option.key}
              htmlFor={inputId}
              className={[
                'flex min-h-[44px] cursor-pointer items-center gap-3 rounded-rs-sm border px-4 py-3 transition duration-300 ease-rs',
                checked
                  ? 'border-rs-blue bg-rs-sky shadow-rs-sm'
                  : 'border-rs-line bg-white hover:border-rs-blue/35 hover:bg-rs-sky-2',
              ].join(' ')}
            >
              <input
                id={inputId}
                type="radio"
                name={question.id}
                value={option.key}
                checked={checked}
                onChange={() => onSelect(option.key)}
                className="size-4 shrink-0 border-rs-line text-rs-blue focus:ring-rs-blue"
              />
              <span className="text-sm font-semibold text-rs-ink">{option.text}</span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
