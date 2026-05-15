import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { startModuleQuiz, type ModuleQuizQuestion, type ModuleQuizStartResponse } from '../lib/api'

export default function ModuleQuizPage() {
  const { courseId, moduleId } = useParams<{ courseId: string; moduleId: string }>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [quiz, setQuiz] = useState<ModuleQuizStartResponse | null>(null)
  const [selectedByQuestionId, setSelectedByQuestionId] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!courseId || !moduleId) {
      setError('Missing course or module.')
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    startModuleQuiz(courseId, moduleId)
      .then((data) => {
        if (!cancelled) setQuiz(data)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load quiz.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [courseId, moduleId])

  const handleSelect = (questionId: string, optionKey: string) => {
    setSelectedByQuestionId((prev) => ({ ...prev, [questionId]: optionKey }))
  }

  return (
    <div className="space-y-8 py-6 sm:py-8">
      <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-6 py-4">
          <Link
            to={courseId ? `/courses/${courseId}` : '/catalog'}
            className="mb-3 inline-flex items-center text-sm text-gray-500 transition-colors hover:text-gray-900"
          >
            <svg className="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to course
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">Module quiz</h1>
          {quiz && (
            <p className="mt-1 text-sm text-gray-500">
              {quiz.questions.length} of {quiz.servedCountN} questions
            </p>
          )}
        </div>

        {loading && (
          <div className="px-6 py-12 text-center text-sm text-gray-500">Loading quiz…</div>
        )}

        {error && !loading && (
          <div className="mx-6 my-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {!loading && !error && quiz && (
          <div className="divide-y divide-gray-100">
            {quiz.questions.map((question, index) => (
              <QuizQuestionBlock
                key={question.id}
                index={index}
                question={question}
                selectedKey={selectedByQuestionId[question.id]}
                onSelect={(key) => handleSelect(question.id, key)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
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
