import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import {
  getCourseProgress,
  isProgressRdsUnavailableError,
  listLessons,
  startModuleQuiz,
  submitModuleQuiz,
  type ModuleQuizLatestSubmission,
  type ModuleQuizQuestion,
  type ModuleQuizResultQuestion,
  type ModuleQuizStartInProgress,
  type ModuleQuizStartResponse,
  type ModuleQuizSubmitResponse,
} from '../lib/api'
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

type ResultsModel = ModuleQuizLatestSubmission | ModuleQuizSubmitResponse

function applyStartResponse(
  data: ModuleQuizStartResponse,
  setTaking: (v: ModuleQuizStartInProgress | null) => void,
  setResults: (v: ResultsModel | null) => void,
  setSelected: (v: Record<string, string>) => void,
) {
  if (data.phase === 'latest_results') {
    setTaking(null)
    setResults(data.latestSubmission)
    setSelected({})
  } else {
    setTaking(data)
    setResults(null)
    setSelected({})
  }
}

export default function ModuleQuizPage() {
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

    startModuleQuiz(courseId, moduleId)
      .then((data) => {
        if (!cancelled) hydrateFromStart(data)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(catalogApiUserMessage(e, 'loadModuleQuiz'))
        }
      })
      .finally(() => {
        if (!cancelled) setPageLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [courseId, moduleId, hydrateFromStart])

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
    <div className="space-y-8 py-6 sm:py-8">
      <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
        <ModuleQuizCardHeader backTo={backTo} taking={taking} results={results} />

        <ModuleQuizCardMain
          pageLoading={pageLoading}
          error={error}
          taking={taking}
          results={results}
          selectedByQuestionId={selectedByQuestionId}
          allAnswered={allAnswered}
          submitting={submitting}
          retakeBusy={retakeBusy}
          onSelect={handleSelect}
          onSubmit={handleSubmit}
          onTryAgain={handleTryAgain}
        />
      </div>
    </div>
  )
}

function ModuleQuizCardHeader({
  backTo,
  taking,
  results,
}: {
  backTo: ModuleQuizReturnTo
  taking: ModuleQuizStartInProgress | null
  results: ResultsModel | null
}) {
  const showTaking = taking !== null
  const showResults = results !== null && taking === null

  return (
    <div className="border-b border-gray-100 px-6 py-4">
      <Link
        to={backTo}
        className="mb-3 inline-flex items-center text-sm text-gray-500 transition-colors hover:text-gray-900"
      >
        <svg className="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        {moduleQuizBackLabel(backTo)}
      </Link>
      <h1 className="text-lg font-semibold text-gray-900">Module quiz</h1>
      {showTaking && taking && (
        <>
          <p className="mt-1 text-sm text-gray-500">
            {taking.questions.length} of {taking.servedCountN} questions
          </p>
          <p className="mt-2 text-sm text-gray-600">
            If you leave this page before submitting, your selected answers will be lost.
          </p>
        </>
      )}
      {showResults && results && (
        <>
          <p className="mt-1 text-sm text-gray-500">
            Attempt {results.attemptNumber} · Score {results.correctCount} / {results.totalCount}
          </p>
          <p className="mt-2 text-sm text-gray-600">These are your latest submitted results.</p>
        </>
      )}
    </div>
  )
}

function ModuleQuizCardMain({
  pageLoading,
  error,
  taking,
  results,
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
  selectedByQuestionId: Record<string, string>
  allAnswered: boolean
  submitting: boolean
  retakeBusy: boolean
  onSelect: (questionId: string, optionKey: string) => void
  onSubmit: () => void
  onTryAgain: () => void
}) {
  const showResults = results !== null && taking === null
  const showTaking = taking !== null
  const submitHelperId = 'module-quiz-submit-helper'

  return (
    <>
      {pageLoading && (
        <div className="px-6 py-12 text-center text-sm text-gray-500">Loading quiz…</div>
      )}

      {error && !pageLoading && (
        <div className="mx-6 my-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {!pageLoading && showTaking && taking && (
        <>
          <div className="divide-y divide-gray-100">
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
          <div className="border-t border-gray-100 px-6 py-4">
            <button
              type="button"
              onClick={onSubmit}
              disabled={!allAnswered || submitting}
              aria-describedby={!allAnswered ? submitHelperId : undefined}
              className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? 'Submitting…' : 'Submit answers'}
            </button>
            {!allAnswered && (
              <p id={submitHelperId} className="mt-2 text-sm text-gray-500">
                Answer every question before submitting.
              </p>
            )}
          </div>
        </>
      )}

      {!pageLoading && showResults && results && (
        <div className="space-y-4 px-6 py-6">
          <QuizResultsBreakdown questions={results.questions} />
          <div className="space-y-2">
            <p className="text-sm text-gray-600">
              Trying again draws a new set of questions from the bank and reshuffles them.
            </p>
            <button
              type="button"
              onClick={onTryAgain}
              disabled={retakeBusy}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {retakeBusy ? 'Starting…' : 'Try again'}
            </button>
          </div>
        </div>
      )}
    </>
  )
}

function QuizResultsBreakdown({ questions }: { questions: ModuleQuizResultQuestion[] }) {
  return (
    <ul className="space-y-6">
      {questions.map((q, index) => (
        <li
          key={q.id}
          className={`rounded-lg border px-4 py-3 ${
            q.isCorrect ? 'border-emerald-200 bg-emerald-50/60' : 'border-amber-200 bg-amber-50/60'
          }`}
        >
          <p className="text-sm font-medium text-gray-900">
            <span className="mr-2 font-normal text-gray-500">Question {index + 1}</span>
            {q.promptText}
          </p>
          <p className="mt-2 text-sm text-gray-700">
            Your answer: <span className="font-medium">{q.selectedOptionKey}</span>
            {' · '}
            Correct answer: <span className="font-medium">{q.correctOptionKey}</span>
            {' · '}
            {q.isCorrect ? (
              <span className="text-emerald-800">Correct</span>
            ) : (
              <span className="text-amber-900">Incorrect</span>
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
    <fieldset className="px-6 py-6">
      <legend className="mb-4 text-base font-medium text-gray-900">
        <span className="mr-2 text-sm font-normal text-gray-500">Question {index + 1}</span>
        {question.promptText}
      </legend>
      <div className="space-y-2">
        {options.map((option) => {
          const inputId = `${question.id}-${option.key}`
          return (
            <label
              key={option.key}
              htmlFor={inputId}
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 px-4 py-3 transition-colors hover:border-indigo-200 hover:bg-indigo-50/50 has-[:checked]:border-indigo-300 has-[:checked]:bg-indigo-50"
            >
              <input
                id={inputId}
                type="radio"
                name={question.id}
                value={option.key}
                checked={selectedKey === option.key}
                onChange={() => onSelect(option.key)}
                className="h-4 w-4 border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-900">{option.text}</span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
