import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { CourseManagementLoadingSkeleton } from '../components/course/CourseManagementPageStates'
import { QuestionBankStudioAddQuestionForm } from '../components/question-banks/QuestionBankStudioAddQuestionForm'
import { QuestionBankStudioLinkedModule } from '../components/question-banks/QuestionBankStudioLinkedModule'
import { QuestionBankStudioPublishPanel } from '../components/question-banks/QuestionBankStudioPublishPanel'
import { QuestionBankStudioQuestionRow } from '../components/question-banks/QuestionBankStudioQuestionRow'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'
import { listCourseModules } from '../lib/api/catalog'
import {
  createQuestionBankQuestion,
  deleteQuestionBankQuestion,
  listCourseModuleQuizzes,
  listCourseQuestionBanks,
  listQuestionBankQuestions,
  publishQuestionBank,
  updateQuestionBankName,
  updateQuestionBankQuestion,
} from '../lib/api/questionBanks'
import type {
  CourseModule,
  CreateQuestionBankQuestionBody,
  ModuleQuizRow,
  PublishQuestionBankBody,
  QuestionBankQuestion,
  QuestionBankSummary,
  UpdateQuestionBankQuestionBody,
} from '../lib/api/types'
import {
  incompleteQuestionBankStudioLinkMessage,
  questionBankUserMessage,
} from '../lib/questionBankErrors'
import {
  questionBankDisplayName,
  questionBankStatusLabel,
  UNTITLED_QUESTION_BANK_LABEL,
} from '../lib/questionBankDisplay'
import { usePageTitle } from '../lib/page-title'

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
      <div className="min-w-0 flex-1">
        <p className="text-sm font-extrabold uppercase tracking-wide text-rs-muted">Question bank studio</p>
        <h1 className="text-3xl font-extrabold tracking-tight text-rs-navy">{bankDisplayName}</h1>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="min-w-[200px] sm:min-w-[280px]">
            <Field
              label="Question bank name"
              value={renameValue}
              maxLength={MAX_BANK_NAME_LENGTH}
              disabled={renaming || bankMissing}
              onChange={(e) => onRenameValueChange(e.target.value)}
            />
          </div>
          <Button type="button" disabled={saveDisabled} onClick={onRename}>
            {renaming ? 'Saving…' : 'Save name'}
          </Button>
        </div>
      </div>
      <Badge tone={bankStatus === 'PUBLISHED' ? 'success' : 'neutral'}>
        {questionBankStatusLabel(bankStatus)}
      </Badge>
    </div>
  )
}

export default function QuestionBankStudioPage() {
  usePageTitle('Question bank')
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
  const mountedRef = useRef(true)
  const loadGenerationRef = useRef(0)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const bank = useMemo(() => banks.find((b) => b.questionBankId === bankId), [banks, bankId])
  const bankDisplayName = bank ? questionBankDisplayName(bank) : UNTITLED_QUESTION_BANK_LABEL

  const linkedModuleRows = useMemo(
    () => moduleQuizzes.filter((r) => r.questionBankId === bankId),
    [moduleQuizzes, bankId],
  )

  useEffect(() => {
    setRenameValue(bankDisplayName)
  }, [bankDisplayName])

  const reload = useCallback(
    async (generation: number) => {
      if (!courseId || !bankId) return
      const requestCourseId = courseId
      const requestBankId = bankId
      const [b, q, m, mods] = await Promise.all([
        listCourseQuestionBanks(requestCourseId),
        listQuestionBankQuestions(requestCourseId, requestBankId),
        listCourseModuleQuizzes(requestCourseId),
        listCourseModules(requestCourseId),
      ])
      if (!mountedRef.current) return
      if (generation !== loadGenerationRef.current) return
      if (requestCourseId !== courseId || requestBankId !== bankId) return
      setBanks(b)
      setQuestions(q)
      setModuleQuizzes(m)
      setCourseModules(mods)
      const found = b.some((row) => row.questionBankId === requestBankId)
      setBankMissing(!found)
    },
    [courseId, bankId],
  )

  useEffect(() => {
    if (!courseId || !bankId) {
      setLoading(false)
      setError(incompleteQuestionBankStudioLinkMessage)
      return
    }
    const generation = ++loadGenerationRef.current
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        setBankMissing(false)
        await reload(generation)
      } catch (err) {
        if (!cancelled) {
          setError(questionBankUserMessage(err, 'loadQuestionBank'))
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
      loadGenerationRef.current += 1
    }
  }, [courseId, bankId, reload])

  const handleAddQuestion = async (body: CreateQuestionBankQuestionBody) => {
    if (!courseId || !bankId) return
    try {
      setCreating(true)
      setError(null)
      await createQuestionBankQuestion(courseId, bankId, body)
      await reload(loadGenerationRef.current)
    } catch (err) {
      if (mountedRef.current) setError(questionBankUserMessage(err, 'saveQuestionBankQuestion'))
      throw err
    } finally {
      if (mountedRef.current) setCreating(false)
    }
  }

  const handlePublish = async (body: PublishQuestionBankBody) => {
    if (!courseId || !bankId) return
    try {
      setPublishing(true)
      setError(null)
      await publishQuestionBank(courseId, bankId, body)
      await reload(loadGenerationRef.current)
      if (mountedRef.current) setEditingQuestionId(null)
    } catch (err) {
      if (mountedRef.current) setError(questionBankUserMessage(err, 'publishQuestionBank'))
    } finally {
      if (mountedRef.current) setPublishing(false)
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
      if (!mountedRef.current) return
      setBanks((prev) =>
        prev.map((row) =>
          row.questionBankId === updated.questionBankId ? { ...row, name: updated.name } : row,
        ),
      )
      setRenameValue(updated.name)
    } catch (err) {
      if (mountedRef.current) setError(questionBankUserMessage(err, 'saveQuestionBank'))
    } finally {
      if (mountedRef.current) setRenaming(false)
    }
  }

  const handleSaveEdit = async (questionId: string, body: UpdateQuestionBankQuestionBody) => {
    if (!courseId || !bankId) return
    try {
      setBusyQuestionId(questionId)
      setError(null)
      await updateQuestionBankQuestion(courseId, bankId, questionId, body)
      await reload(loadGenerationRef.current)
      if (mountedRef.current) setEditingQuestionId(null)
    } catch (err) {
      if (mountedRef.current) setError(questionBankUserMessage(err, 'saveQuestionBankQuestion'))
    } finally {
      if (mountedRef.current) setBusyQuestionId(null)
    }
  }

  const handleDelete = async (questionId: string) => {
    if (!courseId || !bankId) return
    if (!window.confirm('Delete this draft question?')) return
    try {
      setBusyQuestionId(questionId)
      setError(null)
      await deleteQuestionBankQuestion(courseId, bankId, questionId)
      await reload(loadGenerationRef.current)
      if (mountedRef.current && editingQuestionId === questionId) setEditingQuestionId(null)
    } catch (err) {
      if (mountedRef.current) setError(questionBankUserMessage(err, 'deleteQuestionBankQuestion'))
    } finally {
      if (mountedRef.current) setBusyQuestionId(null)
    }
  }

  if (!courseId || !bankId) {
    return (
      <div className="mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
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
      <div className="mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={() => navigate(`/courses/${encodeURIComponent(courseId)}/question-banks`)}
          className="mb-4 text-sm font-semibold text-rs-blue hover:underline"
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
    <div
      className="mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8"
      data-testid="question-bank-studio-loaded"
    >
      <button
        type="button"
        onClick={() => navigate(`/courses/${encodeURIComponent(courseId)}/question-banks`)}
        className="mb-4 text-sm font-semibold text-rs-blue hover:underline"
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
        <div
          className="mb-6 rounded-lg border border-rs-line bg-rs-sky-2 p-4 text-sm font-semibold text-rs-navy"
          role="alert"
        >
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
          <h2 className="mb-3 text-xl font-extrabold text-rs-navy">Questions</h2>
          {questions.length === 0 ? (
            <p className="text-rs-body">No questions yet.</p>
          ) : (
            <Card className="overflow-hidden">
              <ul className="divide-y divide-rs-line">
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
            </Card>
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
