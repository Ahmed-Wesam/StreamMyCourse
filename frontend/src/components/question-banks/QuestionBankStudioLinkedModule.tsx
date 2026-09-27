import type { CourseModule, ModuleQuizRow } from '../../lib/api/types'
import { questionsPerAttemptLabel } from '../../lib/questionBankDisplay'
import { moduleDisplayTitle } from '../../lib/moduleDisplay'

type Props = {
  courseModules: CourseModule[]
  linkedModuleRows: ModuleQuizRow[]
}

const noticeClass =
  'rounded-lg border border-rs-line bg-rs-sky-2 px-3 py-2 text-sm font-semibold text-rs-navy'

export function QuestionBankStudioLinkedModule({ courseModules, linkedModuleRows }: Props) {
  const row = linkedModuleRows[0]

  if (!row) {
    return (
      <p className="mt-2 text-sm font-semibold text-rs-body" data-testid="studio-linked-module" role="status">
        Not attached to a module quiz yet. Attach this bank in course management before publishing.
      </p>
    )
  }

  const title = moduleDisplayTitle(courseModules, row.moduleId)
  const perAttempt = questionsPerAttemptLabel(row.servedCountN)

  return (
    <div className="mt-2 space-y-2">
      {linkedModuleRows.length > 1 ? (
        <p className={noticeClass} role="status" data-testid="studio-linked-multiple-modules-warning">
          This bank is linked to more than one module quiz. The module shown below is the first link
          only. Remove extra links in course management if that is not intended.
        </p>
      ) : null}
      <p className="text-sm text-rs-body" data-testid="studio-linked-module">
        <span className="text-rs-muted">Attached to module: </span>
        <span className="font-semibold text-rs-navy">{title}</span>
        {perAttempt ? <span className="text-rs-muted">{` · ${perAttempt}`}</span> : null}
      </p>
    </div>
  )
}
