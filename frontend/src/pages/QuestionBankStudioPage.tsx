import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { CourseManagementLoadingSkeleton } from '../components/course/CourseManagementPageStates'
import { QuestionBankStudioAddQuestionForm } from '../components/question-banks/QuestionBankStudioAddQuestionForm'
import { QuestionBankStudioPublishPanel } from '../components/question-banks/QuestionBankStudioPublishPanel'
import { QuestionBankStudioQuestionRow } from '../components/question-banks/QuestionBankStudioQuestionRow'
import {
  createQuestionBankQuestion,
  deleteQuestionBankQuestion,
  listCourseModuleQuizzes,
  listCourseQuestionBanks,
  listQuestionBankQuestions,
  publishQuestionBank,
  updateQuestionBankQuestion,
  type CreateQuestionBankQuestionBody,
  type ModuleQuizRow,
  type PublishQuestionBankBody,
  type QuestionBankQuestion,
  type QuestionBankSummary,
  type UpdateQuestionBankQuestionBody,
} from '../lib/api'
import { questionBankUserMessage } from '../lib/questionBankErrors'

export default function QuestionBankStudioPage() {
  const { courseId: courseIdParam, bankId: bankIdParam } = useParams<{ courseId: string; bankId: string }>()
  const navigate = useNavigate()
  const courseId = courseIdParam?.trim() ?? ''
  const bankId = bankIdParam?.trim() ?? ''

  const [banks, setBanks] = useState<QuestionBankSummary[]>([])
  const [questions, setQuestions] = useState<QuestionBankQuestion[]>([])
  const [moduleQuizzes, setModuleQuizzes] = useState<ModuleQuizRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bankMissing, setBankMissing] = useState(false)
  const [creating, setCreating] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null)
  const [busyQuestionId, setBusyQuestionId] = useState<string | null>(null)

  const bank = useMemo(() => banks.find((b) => b.questionBankId === bankId), [banks, bankId])

  const linkedModuleRows = useMemo(
    () => moduleQuizzes.filter((r) => r.questionBankId === bankId),
    [moduleQuizzes, bankId],
  )

  const reload = useCallback(async () => {
    if (!courseId || !bankId) return
    const [b, q, m] = await Promise.all([
      listCourseQuestionBanks(courseId),
      listQuestionBankQuestions(courseId, bankId),
      listCourseModuleQuizzes(courseId),
    ])
    setBanks(b)
    setQuestions(q)
    setModuleQuizzes(m)
    const found = b.some((row) => row.questionBankId === bankId)
    setBankMissing(!found)
  }, [courseId, bankId])

  useEffect(() => {
    if (!courseId || !bankId) {
      setLoading(false)
      setError('Missing course or bank id.')
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        setBankMissing(false)
        await reload()
      } catch (err) {
        if (!cancelled) {
          setError(questionBankUserMessage(err))
          setBanks([])
          setQuestions([])
          setModuleQuizzes([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [courseId, bankId, reload])

  const handleAddQuestion = async (body: CreateQuestionBankQuestionBody) => {
    if (!courseId || !bankId) return
    try {
      setCreating(true)
      setError(null)
      await createQuestionBankQuestion(courseId, bankId, body)
      await reload()
    } catch (err) {
      setError(questionBankUserMessage(err))
      throw err
    } finally {
      setCreating(false)
    }
  }

  const handlePublish = async (body: PublishQuestionBankBody) => {
    if (!courseId || !bankId) return
    try {
      setPublishing(true)
      setError(null)
      await publishQuestionBank(courseId, bankId, body)
      await reload()
      setEditingQuestionId(null)
    } catch (err) {
      setError(questionBankUserMessage(err))
    } finally {
      setPublishing(false)
    }
  }

  const handleSaveEdit = async (questionId: string, body: UpdateQuestionBankQuestionBody) => {
    if (!courseId || !bankId) return
    try {
      setBusyQuestionId(questionId)
      setError(null)
      await updateQuestionBankQuestion(courseId, bankId, questionId, body)
      await reload()
      setEditingQuestionId(null)
    } catch (err) {
      setError(questionBankUserMessage(err))
    } finally {
      setBusyQuestionId(null)
    }
  }

  const handleDelete = async (questionId: string) => {
    if (!courseId || !bankId) return
    if (!window.confirm('Delete this draft question?')) return
    try {
      setBusyQuestionId(questionId)
      setError(null)
      await deleteQuestionBankQuestion(courseId, bankId, questionId)
      await reload()
      if (editingQuestionId === questionId) setEditingQuestionId(null)
    } catch (err) {
      setError(questionBankUserMessage(err))
    } finally {
      setBusyQuestionId(null)
    }
  }

  if (!courseId || !bankId) {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          Missing course or bank id.
        </div>
      </div>
    )
  }

  if (loading) {
    return <CourseManagementLoadingSkeleton />
  }

  if (error && !banks.length && !questions.length) {
    return (
      <div className="mx-auto max-w-4xl">
        <button
          type="button"
          onClick={() => navigate(`/courses/${encodeURIComponent(courseId)}/question-banks`)}
          className="mb-4 text-sm text-blue-600 hover:text-blue-800"
        >
          ← Back to question banks
        </button>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          {error}
        </div>
      </div>
    )
  }

  const bankStatus = bank?.status ?? 'DRAFT'

  return (
    <div className="mx-auto max-w-4xl" data-testid="question-bank-studio-loaded">
      <button
        type="button"
        onClick={() => navigate(`/courses/${encodeURIComponent(courseId)}/question-banks`)}
        className="mb-4 text-sm text-blue-600 hover:text-blue-800"
      >
        ← Back to question banks
      </button>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Question bank studio</h1>
          <p className="mt-1 font-mono text-sm text-gray-600">{bankId}</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            bankStatus === 'PUBLISHED' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
          }`}
        >
          {bankStatus}
        </span>
      </div>

      {bankMissing ? (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900" role="alert">
          This bank is not in the course list (it may have been removed). You can still browse questions if the API
          returns them.
        </div>
      ) : null}

      {error ? (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          {error}
        </div>
      ) : null}

      <div className="space-y-8">
        <section>
          <h2 className="mb-3 text-xl font-semibold text-gray-900">Questions</h2>
          {questions.length === 0 ? (
            <p className="text-gray-600">No questions yet.</p>
          ) : (
            <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white shadow-sm">
              {questions.map((q) => (
                <QuestionBankStudioQuestionRow
                  key={q.questionId}
                  question={q}
                  editing={editingQuestionId === q.questionId}
                  busy={busyQuestionId === q.questionId}
                  onStartEdit={() => setEditingQuestionId(q.questionId)}
                  onCancelEdit={() => setEditingQuestionId(null)}
                  onSave={(body) => handleSaveEdit(q.questionId, body)}
                  onDelete={() => handleDelete(q.questionId)}
                />
              ))}
            </ul>
          )}
        </section>

        <QuestionBankStudioAddQuestionForm
          bankStatus={bankStatus}
          disabled={bankMissing}
          submitting={creating}
          onSubmit={handleAddQuestion}
        />

        <QuestionBankStudioPublishPanel
          bankStatus={bankStatus}
          linkedModuleRows={linkedModuleRows}
          disabled={bankMissing}
          publishing={publishing}
          onPublish={handlePublish}
        />
      </div>
    </div>
  )
}
