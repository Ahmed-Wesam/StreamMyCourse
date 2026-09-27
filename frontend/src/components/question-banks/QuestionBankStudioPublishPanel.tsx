import { useState } from 'react'

import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Field } from '../ui/Field'
import type { ModuleQuizRow, PublishQuestionBankBody, QuestionBankStatus } from '../../lib/api/types'

type Props = {
  bankStatus: QuestionBankStatus
  /** Rows where `questionBankId` matches the current bank. */
  linkedModuleRows: ModuleQuizRow[]
  disabled?: boolean
  publishing?: boolean
  onPublish: (body: PublishQuestionBankBody) => void | Promise<void>
}

const noticeClass =
  'mb-4 rounded-lg border border-rs-line bg-rs-sky-2 px-3 py-2 text-sm font-semibold text-rs-navy'

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
    <Card className="p-4">
      <h3 className="mb-2 text-lg font-extrabold text-rs-navy">Publish bank</h3>
      <p className="mb-4 text-sm text-rs-body">
        Publishing makes questions available to students and sets how many questions each quiz attempt
        includes.
      </p>
      {linkedModuleRows.length === 0 ? (
        <p className={noticeClass} role="status">
          No module quiz is linked to this bank yet. Create or attach a module quiz that uses this bank in course
          management, then return here to publish.
        </p>
      ) : null}
      {linkedModuleRows.length > 1 ? (
        <p className={noticeClass} role="status" data-testid="studio-publish-multiple-modules-warning">
          This bank is linked to more than one module quiz. Publishing will apply to the first linked module only.
          Remove extra links in course management if that is not intended.
        </p>
      ) : null}
      <Field
        label="Questions per attempt"
        type="number"
        min={1}
        value={questionsPerAttempt}
        onChange={(e) => setQuestionsPerAttempt(Number.parseInt(e.target.value, 10) || 1)}
        disabled={linkedModuleRows.length === 0 || disabled || publishing}
        className="mb-0 w-28"
      />
      <Button
        type="button"
        data-testid="studio-publish-submit"
        disabled={!canPublish || !countValid}
        onClick={() => void onPublish({ n: questionsPerAttempt, moduleId: linkedModuleId })}
        className="mt-4"
      >
        {publishing ? 'Publishing…' : 'Publish bank'}
      </Button>
    </Card>
  )
}
