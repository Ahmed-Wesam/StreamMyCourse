import { type FormEvent, useEffect, useState } from 'react'

import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Field } from '../ui/Field'
import type { QuestionBankQuestion, UpdateQuestionBankQuestionBody } from '../../lib/api/types'
import { questionBankStatusLabel } from '../../lib/questionBankDisplay'

type OptionRow = { key: string; text: string }

const rsControl =
  'min-h-[44px] border-[1.5px] border-solid border-rs-line rounded-xl bg-white px-[14px] py-[11px] font-inherit text-[15px] text-rs-ink outline-none transition duration-200 ease-rs leading-normal focus:border-rs-blue focus:shadow-[0_0_0_3px_rgba(30,94,255,.10)] placeholder:text-rs-muted disabled:cursor-not-allowed disabled:opacity-60'

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
            <p className="font-semibold text-rs-navy">{question.promptText}</p>
            <ul className="mt-2 list-inside list-disc text-sm text-rs-body">
              {question.optionsJson.map((o) => (
                <li key={o.key}>
                  {o.text}
                  {question.correctOptionKey === o.key ? (
                    <span className="ml-2 text-xs font-extrabold text-[#0d6f3e]">(correct)</span>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Badge tone={question.status === 'PUBLISHED' ? 'success' : 'neutral'}>
              {questionBankStatusLabel(question.status)}
            </Badge>
            {allowMutate ? (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  data-testid={`studio-question-edit-${question.questionId}`}
                  disabled={busy}
                  onClick={onStartEdit}
                >
                  Edit
                </Button>
                <button
                  type="button"
                  data-testid={`studio-question-delete-${question.questionId}`}
                  disabled={busy}
                  onClick={() => void onDelete()}
                  className="min-h-[44px] rounded-xl border border-red-200 px-3 py-1.5 text-sm font-semibold text-red-700 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Delete
                </button>
              </>
            ) : null}
          </div>
        </div>
      ) : (
        <form
          onSubmit={handleSave}
          className="space-y-3 rounded-lg border border-rs-line bg-rs-sky-2/40 p-3"
        >
          <textarea
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            rows={2}
            className={`${rsControl} w-full`}
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
                className={`${rsControl} w-24 font-mono text-sm`}
                disabled={busy}
              />
              <input
                aria-label={`Edit option ${i + 1} text`}
                value={row.text}
                onChange={(e) =>
                  setRows((prev) => prev.map((r, j) => (j === i ? { ...r, text: e.target.value } : r)))
                }
                className={`${rsControl} min-w-[160px] flex-1`}
                disabled={busy}
              />
            </div>
          ))}
          <button
            type="button"
            className="text-sm font-semibold text-rs-blue hover:underline disabled:cursor-not-allowed disabled:opacity-50"
            disabled={busy || rows.length >= 10}
            onClick={() => setRows((prev) => [...prev, { key: '', text: '' }])}
          >
            Add option
          </button>
          <Field label="Correct answer" className="mb-0">
            <select
              aria-label="Correct answer"
              value={correctKey}
              onChange={(e) => setCorrectKey(e.target.value)}
              disabled={busy}
              className="ml-0 max-w-xs"
            >
              {!hasExistingCorrectKey ? <option value="">—</option> : null}
              {optionKeysForSelect.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={busy}>
              Save
            </Button>
            <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={onCancelEdit}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </li>
  )
}
