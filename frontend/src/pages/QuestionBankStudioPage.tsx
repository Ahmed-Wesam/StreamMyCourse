import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { CourseManagementLoadingSkeleton } from '../components/course/CourseManagementPageStates'
import { QuestionBankStudioAddQuestionForm } from '../components/question-banks/QuestionBankStudioAddQuestionForm'
import { QuestionBankStudioLinkedModule } from '../components/question-banks/QuestionBankStudioLinkedModule'
import { QuestionBankStudioPublishPanel } from '../components/question-banks/QuestionBankStudioPublishPanel'
import { QuestionBankStudioQuestionRow } from '../components/question-banks/QuestionBankStudioQuestionRow'
import {
  createQuestionBankQuestion,
  deleteQuestionBankQuestion,
  listCourseModules,
  listCourseModuleQuizzes,
  listCourseQuestionBanks,
  listQuestionBankQuestions,
  publishQuestionBank,
  updateQuestionBankName,
  updateQuestionBankQuestion,
  type CourseModule,
  type CreateQuestionBankQuestionBody,
  type ModuleQuizRow,
  type PublishQuestionBankBody,
  type QuestionBankQuestion,
  type QuestionBankSummary,
  type UpdateQuestionBankQuestionBody,
} from '../lib/api'
import {
  incompleteQuestionBankStudioLinkMessage,
  questionBankUserMessage,
} from '../lib/questionBankErrors'
import {
  questionBankDisplayName,
  questionBankStatusLabel,
  UNTITLED_QUESTION_BANK_LABEL,
} from '../lib/questionBankDisplay'

const MAX_BANK_NAME_LENGTH = 80

type QuestionBankStudioHeaderProps = {
  bankDisplayName: string
  bankMissing: boolean
  bankStatus: QuestionBankSummary['status']
  renameValue: string
  renaming: boolean
  onRenameValueChange: (value: string) => void
  onRename: () => void
}

function QuestionBankStudioHeader({
  bankDisplayName,
  bankMissing,
  bankStatus,
  renameValue,
  renaming,
  onRenameValueChange,
  onRename,
}: QuestionBankStudioHeaderProps) {
  const saveDisabled = renaming || bankMissing || renameValue.trim() === bankDisplayName

  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-gray-500">Question bank studio</p>
        <h1 className="text-3xl font-bold text-gray-900">{bankDisplayName}</h1>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
            Question bank name
            <input
              type="text"
              value={renameValue}
              maxLength={MAX_BANK_NAME_LENGTH}
              disabled={renaming || bankMissing}
              onChange={(e) => onRenameValueChange(e.target.value)}
              className="min-h-[44px] rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-transparent focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100"
            />
          </label>
          <button
            type="button"
            disabled={saveDisabled}
            onClick={onRename}
            className="min-h-[44px] rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {renaming ? 'Saving…' : 'Save name'}
          </button>
        </div>
      </div>
      <span
        className={`rounded-full px-3 py-1 text-sm font-medium ${
          bankStatus === 'PUBLISHED' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
        }`}
      >
        {questionBankStatusLabel(bankStatus)}
      </span>
    </div>
  )
}

export default function QuestionBankStudioPage() {
  const { courseId: courseIdParam, bankId: bankIdParam } = useParams<{ courseId: string; bankId: string }>()
  const navigate = useNavigate()
  const courseId = courseIdParam?.trim() ?? ''
  const bankId = bankIdParam?.trim() ?? ''

  const [banks, setBanks] = useState<QuestionBankSummary[]>([])
  const [questions, setQuestions] = useState<QuestionBankQuestion[]>([])
  const [courseModules, setCourseModules] = useState<CourseModule[]>([])
  const [moduleQuizzes, setModuleQuizzes] = useState<ModuleQuizRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bankMissing, setBankMissing] = useState(false)
  const [creating, setCreating] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null)
  const [busyQuestionId, setBusyQuestionId] = useState<string | null>(null)

  const bank = useMemo(() => banks.find((b) => b.questionBankId === bankId), [banks, bankId])
  const bankDisplayName = bank ? questionBankDisplayName(bank) : UNTITLED_QUESTION_BANK_LABEL

  const linkedModuleRows = useMemo(
    () => moduleQuizzes.filter((r) => r.questionBankId === bankId),
    [moduleQuizzes, bankId],
  )

  useEffect(() => {
    setRenameValue(bankDisplayName)
  }, [bankDisplayName])

  const reload = useCallback(async () => {
    if (!courseId || !bankId) return
    const [b, q, m, mods] = await Promise.all([
      listCourseQuestionBanks(courseId),
      listQuestionBankQuestions(courseId, bankId),
      listCourseModuleQuizzes(courseId),
      listCourseModules(courseId),
    ])
    setBanks(b)
    setQuestions(q)
    setModuleQuizzes(m)
    setCourseModules(mods)
    const found = b.some((row) => row.questionBankId === bankId)
    setBankMissing(!found)
  }, [courseId, bankId])

  useEffect(() => {
    if (!courseId || !bankId) {
      setLoading(false)
      setError(incompleteQuestionBankStudioLinkMessage)
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
          setCourseModules([])
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

  const handleRename = async () => {
    if (!courseId || !bankId) return
    const name = renameValue.trim()
    if (!name) {
      setError('Enter a question bank name.')
      return
    }
    try {
      setRenaming(true)
      setError(null)
      const updated = await updateQuestionBankName(courseId, bankId, { name })
      setBanks((prev) =>
        prev.map((row) =>
          row.questionBankId === updated.questionBankId ? { ...row, name: updated.name } : row,
        ),
      )
      setRenameValue(updated.name)
    } catch (err) {
      setError(questionBankUserMessage(err))
    } finally {
      setRenaming(false)
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
          {incompleteQuestionBankStudioLinkMessage}
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

      <QuestionBankStudioHeader
        bankDisplayName={bankDisplayName}
        bankMissing={bankMissing}
        bankStatus={bankStatus}
        renameValue={renameValue}
        renaming={renaming}
        onRenameValueChange={setRenameValue}
        onRename={() => void handleRename()}
      />

      <QuestionBankStudioLinkedModule
        courseModules={courseModules}
        linkedModuleRows={linkedModuleRows}
      />

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
