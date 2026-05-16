import { type FormEvent, useEffect, useState } from 'react'

import type { QuestionBankQuestion, UpdateQuestionBankQuestionBody } from '../../lib/api'

type OptionRow = { key: string; text: string }

function optionsToRows(q: QuestionBankQuestion): OptionRow[] {
  const base = q.optionsJson.map((o) => ({ key: o.key, text: o.text }))
  if (base.length < 2) {
    return [...base, ...Array.from({ length: 2 - base.length }, () => ({ key: '', text: '' }))]
  }
  return base
}

type Props = {
  question: QuestionBankQuestion
  editing: boolean
  busy?: boolean
  onStartEdit: () => void
  onCancelEdit: () => void
  onSave: (body: UpdateQuestionBankQuestionBody) => void | Promise<void>
  onDelete: () => void | Promise<void>
}

export function QuestionBankStudioQuestionRow({
  question,
  editing,
  busy = false,
  onStartEdit,
  onCancelEdit,
  onSave,
  onDelete,
}: Props) {
  const [promptText, setPromptText] = useState(question.promptText)
  const [rows, setRows] = useState<OptionRow[]>(() => optionsToRows(question))
  const [correctKey, setCorrectKey] = useState(question.correctOptionKey ?? '')

  useEffect(() => {
    if (editing) {
      setPromptText(question.promptText)
      setRows(optionsToRows(question))
      setCorrectKey(question.correctOptionKey ?? '')
    }
  }, [editing, question])

  const allowMutate = question.status === 'DRAFT'
  const optionKeysForSelect = Array.from(new Set(rows.map((r) => r.key.trim()).filter(Boolean)))
  const hasExistingCorrectKey = Boolean(question.correctOptionKey?.trim())

  const handleSave = (e: FormEvent) => {
    e.preventDefault()
    const optionsJson = rows
      .map((r) => ({ key: r.key.trim(), text: r.text.trim() }))
      .filter((o) => o.key && o.text)
    const body: UpdateQuestionBankQuestionBody = {}
    if (promptText.trim() !== question.promptText) body.promptText = promptText.trim()
    const prevOpts = question.optionsJson.map((o) => ({ key: o.key, text: o.text }))
    const same =
      optionsJson.length === prevOpts.length &&
      optionsJson.every((o, i) => o.key === prevOpts[i]?.key && o.text === prevOpts[i]?.text)
    if (!same) body.optionsJson = optionsJson
    const ck = correctKey.trim() || undefined
    const prevCk = question.correctOptionKey ?? ''
    if (ck !== prevCk) body.correctOptionKey = ck
    if (Object.keys(body).length === 0) {
      onCancelEdit()
      return
    }
    void onSave(body)
  }

  return (
    <li className="px-4 py-4">
      {!editing ? (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <p className="font-medium text-gray-900">{question.promptText}</p>
            <ul className="mt-2 list-inside list-disc text-sm text-gray-600">
              {question.optionsJson.map((o) => (
                <li key={o.key}>
                  <span className="font-mono text-xs">{o.key}</span>: {o.text}
                </li>
              ))}
            </ul>
            {question.correctOptionKey ? (
              <p className="mt-1 text-xs text-gray-500">Correct: {question.correctOptionKey}</p>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2 py-1 text-xs font-medium ${
                question.status === 'PUBLISHED'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {question.status}
            </span>
            {allowMutate ? (
              <>
                <button
                  type="button"
                  data-testid={`studio-question-edit-${question.questionId}`}
                  disabled={busy}
                  onClick={onStartEdit}
                  className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
                >
                  Edit
                </button>
                <button
                  type="button"
                  data-testid={`studio-question-delete-${question.questionId}`}
                  disabled={busy}
                  onClick={() => void onDelete()}
                  className="rounded border border-red-200 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
                >
                  Delete
                </button>
              </>
            ) : null}
          </div>
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-3 rounded-lg border border-blue-100 bg-blue-50/40 p-3">
          <textarea
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            disabled={busy}
          />
          {rows.map((row, i) => (
            <div key={i} className="flex flex-wrap gap-2">
              <input
                aria-label={`Edit option ${i + 1} key`}
                value={row.key}
                onChange={(e) =>
                  setRows((prev) => prev.map((r, j) => (j === i ? { ...r, key: e.target.value } : r)))
                }
                className="w-24 rounded border border-gray-300 px-2 py-1.5 text-sm font-mono"
                disabled={busy}
              />
              <input
                aria-label={`Edit option ${i + 1} text`}
                value={row.text}
                onChange={(e) =>
                  setRows((prev) => prev.map((r, j) => (j === i ? { ...r, text: e.target.value } : r)))
                }
                className="min-w-[160px] flex-1 rounded border border-gray-300 px-2 py-1.5 text-sm"
                disabled={busy}
              />
            </div>
          ))}
          <button
            type="button"
            className="text-sm text-blue-600 hover:text-blue-800"
            disabled={busy || rows.length >= 10}
            onClick={() => setRows((prev) => [...prev, { key: '', text: '' }])}
          >
            Add option
          </button>
          <div>
            <label className="text-sm text-gray-700">Correct key</label>
            <select
              aria-label="Correct key"
              value={correctKey}
              onChange={(e) => setCorrectKey(e.target.value)}
              disabled={busy}
              className="ml-2 rounded border border-gray-300 px-2 py-1 text-sm"
            >
              {!hasExistingCorrectKey ? <option value="">—</option> : null}
              {optionKeysForSelect.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Save
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={onCancelEdit}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </li>
  )
}
