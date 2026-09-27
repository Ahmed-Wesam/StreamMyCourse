import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import type { CourseModule, ModuleQuizRow, QuestionBankSummary } from '../../lib/api/types'
import {
  questionBankDisplayName,
  questionBankStatusLabel,
  questionsPerAttemptLabel,
  UNTITLED_QUESTION_BANK_LABEL,
} from '../../lib/questionBankDisplay'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Field } from '../ui/Field'

type Props = {
  courseId: string
  sortedModules: CourseModule[]
  moduleQuizRows: ModuleQuizRow[]
  questionBankSummaries: QuestionBankSummary[]
  attachingModuleId?: string | null
  onAttachQuiz: (moduleId: string, questionBankId: string) => void | Promise<void>
}

function needsAttachUi(row: ModuleQuizRow | undefined): boolean {
  return !row || row.questionBankId == null || row.questionBankId === ''
}

function banksAvailableForModule(
  moduleId: string,
  banks: QuestionBankSummary[],
  moduleQuizRows: ModuleQuizRow[],
): QuestionBankSummary[] {
  return banks.filter(
    (b) =>
      !moduleQuizRows.some(
        (r) => r.questionBankId === b.questionBankId && r.moduleId !== moduleId,
      ),
  )
}

export function CourseManagementModuleQuizPanel({
  courseId,
  sortedModules,
  moduleQuizRows,
  questionBankSummaries,
  attachingModuleId = null,
  onAttachQuiz,
}: Props) {
  const banksLink = `/courses/${encodeURIComponent(courseId)}/question-banks`
  const [selectedBankByModuleId, setSelectedBankByModuleId] = useState<Record<string, string>>({})

  const moduleIdsKey = useMemo(
    () =>
      [...sortedModules.map((m) => m.id)]
        .sort()
        .join(','),
    [sortedModules],
  )

  useEffect(() => {
    const idSet = new Set(moduleIdsKey.split(',').filter(Boolean))
    setSelectedBankByModuleId((prev) => {
      const next: Record<string, string> = {}
      for (const k of Object.keys(prev)) {
        if (idSet.has(k)) next[k] = prev[k]
      }
      return Object.keys(next).length === Object.keys(prev).length ? prev : next
    })
  }, [moduleIdsKey])

  return (
    <Card
      className="mb-6 p-6"
      data-testid="course-management-module-quizzes"
      data-question-bank-count={questionBankSummaries.length}
      aria-labelledby="course-management-module-quizzes-heading"
    >
      <h2 id="course-management-module-quizzes-heading" className="mb-4 text-xl font-extrabold text-rs-navy">
        Module quizzes
      </h2>

      {sortedModules.length === 0 ? (
        <p className="text-sm text-rs-body">Add a module first to attach bank quizzes.</p>
      ) : (
        <ul className="space-y-3">
          {sortedModules.map((m) => {
            const row = moduleQuizRows.find((r) => r.moduleId === m.id)
            const showAttach = needsAttachUi(row)
            const selectedBankId = selectedBankByModuleId[m.id] ?? ''
            const busy = attachingModuleId === m.id
            const linkedBank = row?.questionBankId
              ? questionBankSummaries.find((b) => b.questionBankId === row.questionBankId)
              : undefined
            const availableBanks = banksAvailableForModule(m.id, questionBankSummaries, moduleQuizRows)

            return (
              <li
                key={m.id}
                className="flex flex-col gap-3 rounded-lg border border-rs-line bg-rs-sky-2/40 px-4 py-3 text-sm sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="min-w-0">
                  <div className="font-semibold text-rs-navy">{m.title}</div>
                  {!showAttach && row?.questionBankId ? (
                    <div className="mt-2 space-y-1 text-rs-body">
                      <div>
                        <span className="text-rs-muted">Question bank: </span>
                        <span className="font-semibold">
                          {linkedBank ? questionBankDisplayName(linkedBank) : UNTITLED_QUESTION_BANK_LABEL}
                        </span>
                      </div>
                      <div>
                        <span className="text-rs-muted">Questions per attempt: </span>
                        <span>{questionsPerAttemptLabel(row.servedCountN) ?? 'Not set yet'}</span>
                      </div>
                      <p className="text-xs text-rs-muted">
                        The linked question bank cannot be changed after a quiz is attached.
                      </p>
                    </div>
                  ) : null}
                </div>

                <div className="flex shrink-0 flex-col gap-2 sm:items-end">
                  {showAttach ? (
                    questionBankSummaries.length === 0 ? (
                      <div className="max-w-md text-right text-rs-body">
                        <p className="mb-1">No question banks for this course yet.</p>
                        <Link to={banksLink} className="font-semibold text-rs-blue hover:underline">
                          Create or open question banks
                        </Link>
                      </div>
                    ) : availableBanks.length === 0 ? (
                      <div className="max-w-md text-right text-rs-body">
                        <p className="mb-1">All question banks are already linked to other modules.</p>
                        <Link to={banksLink} className="font-semibold text-rs-blue hover:underline">
                          Open question banks
                        </Link>
                      </div>
                    ) : (
                      <div className="flex flex-col items-stretch gap-2 sm:items-end">
                        <Field label="Question bank" className="mb-0 min-w-[12rem]">
                          <select
                            className="!py-2 !text-sm"
                            value={selectedBankId}
                            disabled={busy}
                            onChange={(e) =>
                              setSelectedBankByModuleId((prev) => ({ ...prev, [m.id]: e.target.value }))
                            }
                          >
                            <option value="">Select a bank…</option>
                            {availableBanks.map((b) => (
                              <option key={b.questionBankId} value={b.questionBankId}>
                                {questionBankDisplayName(b)} ({questionBankStatusLabel(b.status)})
                              </option>
                            ))}
                          </select>
                        </Field>
                        <Button
                          type="button"
                          size="sm"
                          disabled={!selectedBankId || busy}
                          onClick={() => {
                            if (!selectedBankId) return
                            void onAttachQuiz(m.id, selectedBankId)
                          }}
                        >
                          Attach quiz
                        </Button>
                      </div>
                    )
                  ) : (
                    <span className="self-start text-rs-body sm:self-end">Quiz linked</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}
