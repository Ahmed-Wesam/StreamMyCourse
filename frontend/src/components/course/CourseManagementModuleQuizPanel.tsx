import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import type { CourseModule, ModuleQuizRow, QuestionBankSummary } from '../../lib/api'

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
    <section
      className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
      data-testid="course-management-module-quizzes"
      data-question-bank-count={questionBankSummaries.length}
      aria-labelledby="course-management-module-quizzes-heading"
    >
      <h2 id="course-management-module-quizzes-heading" className="mb-4 text-xl font-semibold text-gray-900">
        Module quizzes
      </h2>

      {sortedModules.length === 0 ? (
        <p className="text-sm text-gray-600">Add a module first to attach bank quizzes.</p>
      ) : (
        <ul className="space-y-3">
          {sortedModules.map((m) => {
            const row = moduleQuizRows.find((r) => r.moduleId === m.id)
            const showAttach = needsAttachUi(row)
            const selectId = `course-management-module-qb-${m.id}`
            const selectedBankId = selectedBankByModuleId[m.id] ?? ''
            const busy = attachingModuleId === m.id

            return (
              <li
                key={m.id}
                className="flex flex-col gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-sm sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="min-w-0">
                  <div className="font-medium text-gray-900">{m.title}</div>
                  {!showAttach && row?.questionBankId ? (
                    <div className="mt-2 space-y-1 text-gray-700">
                      <div>
                        <span className="text-gray-500">Question bank: </span>
                        <span className="font-mono text-xs">{row.questionBankId}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Served (n): </span>
                        <span>{row.servedCountN ?? '—'}</span>
                      </div>
                      <p className="text-xs text-gray-500">
                        The linked question bank cannot be changed after a quiz is attached.
                      </p>
                    </div>
                  ) : null}
                </div>

                <div className="flex shrink-0 flex-col gap-2 sm:items-end">
                  {showAttach ? (
                    questionBankSummaries.length === 0 ? (
                      <div className="max-w-md text-right text-gray-600">
                        <p className="mb-1">No question banks for this course yet.</p>
                        <Link to={banksLink} className="text-blue-600 hover:text-blue-800">
                          Create or open question banks
                        </Link>
                      </div>
                    ) : (
                      <div className="flex flex-col items-stretch gap-2 sm:items-end">
                        <div className="flex flex-col gap-1">
                          <label htmlFor={selectId} className="text-left text-xs font-medium text-gray-700">
                            Question bank
                          </label>
                          <select
                            id={selectId}
                            className="min-w-[12rem] rounded-md border border-gray-300 bg-white px-2 py-2 text-sm text-gray-900"
                            value={selectedBankId}
                            disabled={busy}
                            onChange={(e) =>
                              setSelectedBankByModuleId((prev) => ({ ...prev, [m.id]: e.target.value }))
                            }
                          >
                            <option value="">Select a bank…</option>
                            {questionBankSummaries.map((b) => (
                              <option key={b.questionBankId} value={b.questionBankId}>
                                {b.questionBankId} ({b.status})
                              </option>
                            ))}
                          </select>
                        </div>
                        <button
                          type="button"
                          className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={!selectedBankId || busy}
                          onClick={() => {
                            if (!selectedBankId) return
                            void onAttachQuiz(m.id, selectedBankId)
                          }}
                        >
                          Attach quiz
                        </button>
                      </div>
                    )
                  ) : (
                    <span className="self-start text-gray-600 sm:self-end">Quiz linked</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
