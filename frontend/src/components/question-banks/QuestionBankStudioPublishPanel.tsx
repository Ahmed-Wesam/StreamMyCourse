import { useState } from 'react'

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
  const [questionsPerAttempt, setQuestionsPerAttempt] = useState(5)
  const linkedModuleId = linkedModuleRows[0]?.moduleId ?? ''

  if (bankStatus !== 'DRAFT') return null

  const canPublish = linkedModuleRows.length > 0 && linkedModuleId && !disabled && !publishing
  const countValid = Number.isFinite(questionsPerAttempt) && questionsPerAttempt >= 1

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-2 text-lg font-semibold text-gray-900">Publish bank</h3>
      <p className="mb-4 text-sm text-gray-600">
        Publishing makes questions available to students and sets how many questions each quiz attempt
        includes.
      </p>
      {linkedModuleRows.length === 0 ? (
        <p className="mb-4 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="status">
          No module quiz is linked to this bank yet. Create or attach a module quiz that uses this bank in course
          management, then return here to publish.
        </p>
      ) : null}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="studio-publish-n">
          Questions per attempt
        </label>
        <input
          id="studio-publish-n"
          type="number"
          min={1}
          value={questionsPerAttempt}
          onChange={(e) => setQuestionsPerAttempt(Number.parseInt(e.target.value, 10) || 1)}
          disabled={linkedModuleRows.length === 0 || disabled || publishing}
          className="min-h-[44px] w-28 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <button
        type="button"
        data-testid="studio-publish-submit"
        disabled={!canPublish || !countValid}
        onClick={() => void onPublish({ n: questionsPerAttempt, moduleId: linkedModuleId })}
        className="mt-4 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {publishing ? 'Publishing…' : 'Publish bank'}
      </button>
    </div>
  )
}
