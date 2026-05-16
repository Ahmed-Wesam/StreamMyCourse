import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { CourseManagementLoadingSkeleton } from '../components/course/CourseManagementPageStates'
import {
  ApiError,
  createQuestionBank,
  listCourseQuestionBanks,
  type QuestionBankSummary,
} from '../lib/api'

export default function QuestionBanksListPage() {
  const { courseId: courseIdParam } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const courseId = courseIdParam?.trim() ?? ''

  const [banks, setBanks] = useState<QuestionBankSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    if (!courseId) {
      setBanks([])
      setError('Missing course id.')
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
      setError(err instanceof Error ? err.message : 'Failed to load question banks')
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    void load()
  }, [load])

  const handleCreate = async () => {
    if (!courseId || creating) return
    try {
      setCreating(true)
      setError(null)
      const { questionBankId } = await createQuestionBank(courseId)
      const c = encodeURIComponent(courseId)
      const b = encodeURIComponent(questionBankId)
      navigate(`/courses/${c}/question-banks/${b}`)
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Failed to create bank'
      setError(msg)
    } finally {
      setCreating(false)
    }
  }

  if (!courseId) {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700" role="alert">
          Missing course id.
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
          <button
            type="button"
            data-testid="question-banks-create"
            disabled={creating}
            onClick={() => void handleCreate()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creating ? 'Creating…' : 'Create bank'}
          </button>
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
                  <span className="font-mono text-sm">{bank.questionBankId}</span>
                  <span className="text-sm text-gray-600">{bank.status}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
