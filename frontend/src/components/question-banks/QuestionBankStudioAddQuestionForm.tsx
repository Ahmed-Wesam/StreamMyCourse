import { type FormEvent, useCallback, useState } from 'react'

import type { CreateQuestionBankQuestionBody } from '../../lib/api'

type OptionRow = { key: string; text: string }

const initialRows = (): OptionRow[] => [
  { key: '', text: '' },
  { key: '', text: '' },
]

type Props = {
  disabled?: boolean
  submitting?: boolean
  onSubmit: (body: CreateQuestionBankQuestionBody) => void | Promise<void>
}

export function QuestionBankStudioAddQuestionForm({
  disabled = false,
  submitting = false,
  onSubmit,
}: Props) {
  const [promptText, setPromptText] = useState('')
  const [rows, setRows] = useState<OptionRow[]>(initialRows)
  const [correctKey, setCorrectKey] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const optionKeysForSelect = Array.from(new Set(rows.map((r) => r.key.trim()).filter(Boolean)))

  const resetForm = useCallback(() => {
    setPromptText('')
    setRows(initialRows())
    setCorrectKey('')
    setLocalError(null)
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLocalError(null)
    const optionsJson = rows
      .map((r) => ({ key: r.key.trim(), text: r.text.trim() }))
      .filter((o) => o.key && o.text)
    if (optionsJson.length < 2) {
      setLocalError('Add at least two answer choices with text.')
      return
    }
    if (!correctKey.trim()) {
      setLocalError('Choose the correct answer.')
      return
    }
    const body: CreateQuestionBankQuestionBody = {
      promptText: promptText.trim(),
      optionsJson,
      correctOptionKey: correctKey.trim(),
    }
    try {
      await onSubmit(body)
      resetForm()
    } catch {
      /* parent surfaces API errors */
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-lg font-semibold text-gray-900">Add question</h3>
      {localError ? (
        <div className="mb-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="alert">
          {localError}
        </div>
      ) : null}
      <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="studio-question-prompt">
        Prompt
      </label>
      <textarea
        id="studio-question-prompt"
        data-testid="studio-question-prompt"
        value={promptText}
        onChange={(e) => setPromptText(e.target.value)}
        rows={3}
        className="mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500"
        disabled={disabled || submitting}
      />
      <div className="mb-2 text-sm font-medium text-gray-700">Options</div>
      <div className="space-y-2">
        {rows.map((row, i) => (
          <div key={i} className="flex flex-wrap gap-2">
            <input
              data-testid={`studio-option-key-${i}`}
              aria-label={`Option ${i + 1} label`}
              value={row.key}
              onChange={(e) =>
                setRows((prev) => prev.map((r, j) => (j === i ? { ...r, key: e.target.value } : r)))
              }
              placeholder="A"
              className="w-24 min-h-[44px] rounded-lg border border-gray-300 px-2 py-2 text-sm font-mono focus:border-transparent focus:ring-2 focus:ring-blue-500"
              disabled={disabled || submitting}
            />
            <input
              data-testid={`studio-option-text-${i}`}
              aria-label={`Option ${i + 1} text`}
              value={row.text}
              onChange={(e) =>
                setRows((prev) => prev.map((r, j) => (j === i ? { ...r, text: e.target.value } : r)))
              }
              placeholder="Answer text"
              className="min-h-[44px] min-w-[200px] flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500"
              disabled={disabled || submitting}
            />
          </div>
        ))}
      </div>
      <button
        type="button"
        data-testid="studio-add-option"
        onClick={() => setRows((prev) => [...prev, { key: '', text: '' }])}
        disabled={disabled || submitting || rows.length >= 10}
        className="mt-2 text-sm font-medium text-blue-600 hover:text-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Add option row
      </button>
      <div className="mt-4">
        <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="studio-correct-select">
          Correct answer (required)
        </label>
        <select
          id="studio-correct-select"
          data-testid="studio-correct-select"
          value={correctKey}
          onChange={(e) => setCorrectKey(e.target.value)}
          disabled={disabled || submitting}
          className="min-h-[44px] w-full max-w-xs rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:ring-2 focus:ring-blue-500"
        >
          <option value="">—</option>
          {optionKeysForSelect.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        data-testid="studio-add-question-submit"
        disabled={disabled || submitting}
        className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? 'Saving…' : 'Add question'}
      </button>
    </form>
  )
}
