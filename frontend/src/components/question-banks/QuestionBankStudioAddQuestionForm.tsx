import { type FormEvent, useCallback, useState } from 'react'

import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Field } from '../ui/Field'
import type { CreateQuestionBankQuestionBody } from '../../lib/api/types'

type OptionRow = { key: string; text: string }

const initialRows = (): OptionRow[] => [
  { key: '', text: '' },
  { key: '', text: '' },
]

const rsControl =
  'min-h-[44px] w-full border-[1.5px] border-solid border-rs-line rounded-xl bg-white px-[14px] py-[11px] font-inherit text-[15px] text-rs-ink outline-none transition duration-200 ease-rs leading-normal focus:border-rs-blue focus:shadow-[0_0_0_3px_rgba(30,94,255,.10)] placeholder:text-rs-muted disabled:cursor-not-allowed disabled:opacity-60'

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
    <form onSubmit={handleSubmit}>
      <Card className="p-4">
      <h3 className="mb-3 text-lg font-extrabold text-rs-navy">Add question</h3>
      {localError ? (
        <div
          className="mb-3 rounded-lg border border-rs-line bg-rs-sky-2 px-3 py-2 text-sm font-semibold text-rs-navy"
          role="alert"
        >
          {localError}
        </div>
      ) : null}
      <Field label="Prompt" className="mb-4">
        <textarea
          data-testid="studio-question-prompt"
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
          rows={3}
          disabled={disabled || submitting}
        />
      </Field>
      <div className="mb-2 text-[13px] font-bold text-rs-navy">Options</div>
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
              className={`${rsControl} w-24 font-mono text-sm`}
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
              className={`${rsControl} min-w-[200px] flex-1`}
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
        className="mt-2 text-sm font-semibold text-rs-blue hover:underline disabled:cursor-not-allowed disabled:opacity-50"
      >
        Add option row
      </button>
      <Field label="Correct answer (required)" className="mb-0 mt-4">
        <select
          data-testid="studio-correct-select"
          value={correctKey}
          onChange={(e) => setCorrectKey(e.target.value)}
          disabled={disabled || submitting}
          className="max-w-xs"
        >
          <option value="">—</option>
          {optionKeysForSelect.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
      </Field>
      <Button
        type="submit"
        data-testid="studio-add-question-submit"
        disabled={disabled || submitting}
        className="mt-4"
      >
        {submitting ? 'Saving…' : 'Add question'}
      </Button>
      </Card>
    </form>
  )
}
