import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { CourseManagementLoadingSkeleton } from '../components/course/CourseManagementPageStates'
import { createQuestionBank, listCourseQuestionBanks, type QuestionBankSummary } from '../lib/api'
import { questionBankDisplayName, questionBankStatusLabel } from '../lib/questionBankDisplay'
import {
  incompleteQuestionBanksListLinkMessage,
  questionBankUserMessage,
} from '../lib/questionBankErrors'

const MAX_BANK_NAME_LENGTH = 80

export default function QuestionBanksListPage() {
  const { courseId: courseIdParam } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const courseId = courseIdParam?.trim() ?? ''

  const [banks, setBanks] = useState<QuestionBankSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [newBankName, setNewBankName] = useState('')

  const load = useCallback(async () => {
    if (!courseId) {
      setBanks([])
      setError(incompleteQuestionBanksListLinkMessage)
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      setError(null)
      const rows = await listCourseQuestionBanks(courseId)
      setBanks(rows)
    } catch (err) {
      setBanks([])
      setError(questionBankUserMessage(err, 'loadQuestionBanks'))
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    void load()
  }, [load])

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
      const c = encodeURIComponent(courseId)
      const b = encodeURIComponent(questionBankId)
      navigate(`/courses/${c}/question-banks/${b}`)
    } catch (err) {
      setError(questionBankUserMessage(err, 'createQuestionBank'))
    } finally {
      setCreating(false)
    }
  }

  if (!courseId) {
    return (
      <div className="mx-auto max-w-4xl">
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
    <div className="mx-auto max-w-4xl">
      <div className="mb-8">
        <button
          type="button"
          onClick={() => navigate(`/courses/${encodeURIComponent(courseId)}`)}
          className="mb-2 text-sm text-blue-600 hover:text-blue-800"
        >
          ← Back to course
        </button>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-3xl font-bold text-gray-900">Question banks</h1>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="flex flex-col gap-1 text-sm font-medium text-gray-700">
              New bank name
              <input
                type="text"
                value={newBankName}
                maxLength={MAX_BANK_NAME_LENGTH}
                onChange={(e) => setNewBankName(e.target.value)}
                className="min-h-[44px] rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. Chapter 1 quiz"
              />
            </label>
            <button
              type="button"
              data-testid="question-banks-create"
              disabled={creating}
              onClick={() => void handleCreate()}
              className="min-h-[44px] rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {creating ? 'Creating…' : 'Create bank'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          {error}
        </div>
      )}

      {banks.length === 0 ? (
        <p className="text-gray-600">No question banks yet. Create one to get started.</p>
      ) : (
        <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white shadow-sm">
          {banks.map((bank) => {
            const to = `/courses/${encodeURIComponent(courseId)}/question-banks/${encodeURIComponent(bank.questionBankId)}`
            return (
              <li key={bank.questionBankId}>
                <Link
                  to={to}
                  className="flex items-center justify-between gap-4 px-4 py-3 text-gray-900 hover:bg-gray-50"
                >
                  <span className="min-w-0 truncate font-medium">{questionBankDisplayName(bank)}</span>
                  <span className="text-sm text-gray-600">{questionBankStatusLabel(bank.status)}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
