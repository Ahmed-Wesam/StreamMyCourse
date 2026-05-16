import { useEffect, useState } from 'react'

import type { ModuleQuizRow, PublishQuestionBankBody, QuestionBankStatus } from '../../lib/api'

type Props = {
  bankStatus: QuestionBankStatus
  /** Rows where `questionBankId` matches the current bank. */
  linkedModuleRows: ModuleQuizRow[]
  disabled?: boolean
  publishing?: boolean
  onPublish: (body: PublishQuestionBankBody) => void | Promise<void>
}

export function QuestionBankStudioPublishPanel({
  bankStatus,
  linkedModuleRows,
  disabled = false,
  publishing = false,
  onPublish,
}: Props) {
  const [n, setN] = useState(5)
  const [moduleId, setModuleId] = useState('')

  useEffect(() => {
    if (linkedModuleRows.length === 0) {
      setModuleId('')
      return
    }
    if (!linkedModuleRows.some((r) => r.moduleId === moduleId)) {
      setModuleId(linkedModuleRows[0]!.moduleId)
    }
  }, [linkedModuleRows, moduleId])

  if (bankStatus !== 'DRAFT') return null

  const canPublish = linkedModuleRows.length > 0 && moduleId && !disabled && !publishing
  const nValid = Number.isFinite(n) && n >= 1

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-2 text-lg font-semibold text-gray-900">Publish bank</h3>
      <p className="mb-4 text-sm text-gray-600">
        Publishing attaches this bank to the selected module quiz and fixes the served question count.
      </p>
      {linkedModuleRows.length === 0 ? (
        <p className="mb-4 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="status">
          No module quiz is linked to this bank yet. Create or attach a module quiz that uses this bank in course
          management, then return here to publish.
        </p>
      ) : null}
      <div className="flex flex-wrap gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="studio-publish-n">
            Served count (N)
          </label>
          <input
            id="studio-publish-n"
            type="number"
            min={1}
            value={n}
            onChange={(e) => setN(Number.parseInt(e.target.value, 10) || 1)}
            disabled={linkedModuleRows.length === 0 || disabled || publishing}
            className="min-h-[44px] w-28 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="min-w-[200px] flex-1">
          <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="studio-publish-module">
            Module
          </label>
          <select
            id="studio-publish-module"
            value={moduleId}
            onChange={(e) => setModuleId(e.target.value)}
            disabled={!linkedModuleRows.length || disabled || publishing}
            className="min-h-[44px] w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500"
          >
            {linkedModuleRows.length === 0 ? (
              <option value="">—</option>
            ) : (
              linkedModuleRows.map((r) => (
                <option key={r.quizId} value={r.moduleId}>
                  {r.moduleId}
                </option>
              ))
            )}
          </select>
        </div>
      </div>
      <button
        type="button"
        data-testid="studio-publish-submit"
        disabled={!canPublish || !nValid}
        onClick={() => void onPublish({ n, moduleId })}
        className="mt-4 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {publishing ? 'Publishing…' : 'Publish bank'}
      </button>
    </div>
  )
}
