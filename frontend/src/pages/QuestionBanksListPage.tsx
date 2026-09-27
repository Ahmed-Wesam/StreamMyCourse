import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { CourseManagementLoadingSkeleton } from '../components/course/CourseManagementPageStates'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'
import { createQuestionBank, listCourseQuestionBanks } from '../lib/api/questionBanks'
import type { QuestionBankSummary } from '../lib/api/types'
import { questionBankDisplayName, questionBankStatusLabel } from '../lib/questionBankDisplay'
import {
  incompleteQuestionBanksListLinkMessage,
  questionBankUserMessage,
} from '../lib/questionBankErrors'
import { usePageTitle } from '../lib/page-title'

const MAX_BANK_NAME_LENGTH = 80

export default function QuestionBanksListPage() {
  usePageTitle('Question bank')
  const { courseId: courseIdParam } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const courseId = courseIdParam?.trim() ?? ''

  const [banks, setBanks] = useState<QuestionBankSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [newBankName, setNewBankName] = useState('')
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!courseId) {
      setBanks([])
      setError(incompleteQuestionBanksListLinkMessage)
      setLoading(false)
      return
    }

    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        const rows = await listCourseQuestionBanks(courseId)
        if (!cancelled) setBanks(rows)
      } catch (err) {
        if (!cancelled) {
          setBanks([])
          setError(questionBankUserMessage(err, 'loadQuestionBanks'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [courseId])

  const handleCreate = async () => {
    if (!courseId || creating) return
    const name = newBankName.trim()
    if (!name) {
      setError('Enter a question bank name.')
      return
    }
    try {
      setCreating(true)
      setError(null)
      const { questionBankId } = await createQuestionBank(courseId, { name })
      if (!mountedRef.current) return
      const c = encodeURIComponent(courseId)
      const b = encodeURIComponent(questionBankId)
      navigate(`/courses/${c}/question-banks/${b}`)
    } catch (err) {
      if (mountedRef.current) setError(questionBankUserMessage(err, 'createQuestionBank'))
    } finally {
      if (mountedRef.current) setCreating(false)
    }
  }

  if (!courseId) {
    return (
      <div className="mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          {incompleteQuestionBanksListLinkMessage}
        </div>
      </div>
    )
  }

  if (loading) {
    return <CourseManagementLoadingSkeleton />
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
      <div className="mb-8">
        <button
          type="button"
          onClick={() => navigate(`/courses/${encodeURIComponent(courseId)}`)}
          className="mb-2 text-sm font-semibold text-rs-blue hover:underline"
        >
          ← Back to course
        </button>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-3xl font-extrabold tracking-tight text-rs-navy">Question banks</h1>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <div className="min-w-[200px] sm:min-w-[240px]">
              <Field
                label="New bank name"
                value={newBankName}
                maxLength={MAX_BANK_NAME_LENGTH}
                onChange={(e) => setNewBankName(e.target.value)}
                placeholder="e.g. Chapter 1 quiz"
                className="mb-0"
              />
            </div>
            <Button
              type="button"
              data-testid="question-banks-create"
              disabled={creating}
              onClick={() => void handleCreate()}
            >
              {creating ? 'Creating…' : 'Create bank'}
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          {error}
        </div>
      )}

      {banks.length === 0 ? (
        <p className="text-rs-body">No question banks yet. Create one to get started.</p>
      ) : (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-rs-line">
            {banks.map((bank) => {
              const to = `/courses/${encodeURIComponent(courseId)}/question-banks/${encodeURIComponent(bank.questionBankId)}`
              return (
                <li key={bank.questionBankId}>
                  <Link
                    to={to}
                    className="flex items-center justify-between gap-4 px-4 py-3 transition-colors hover:bg-rs-sky-2/40"
                  >
                    <span className="min-w-0 truncate font-semibold text-rs-navy">
                      {questionBankDisplayName(bank)}
                    </span>
                    <Badge tone={bank.status === 'PUBLISHED' ? 'success' : 'neutral'}>
                      {questionBankStatusLabel(bank.status)}
                    </Badge>
                  </Link>
                </li>
              )
            })}
          </ul>
        </Card>
      )}
    </div>
  )
}
