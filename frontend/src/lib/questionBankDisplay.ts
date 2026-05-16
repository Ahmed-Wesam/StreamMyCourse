import type { QuestionBankStatus, QuestionBankSummary } from './api'

export const UNTITLED_QUESTION_BANK_LABEL = 'Untitled question bank'

export function questionBankDisplayName(bank: Pick<QuestionBankSummary, 'questionBankId' | 'name'>): string {
  const name = typeof bank.name === 'string' ? bank.name.trim() : ''
  return name || UNTITLED_QUESTION_BANK_LABEL
}

export function questionBankStatusLabel(status: QuestionBankStatus): string {
  return status === 'PUBLISHED' ? 'Published' : 'Draft'
}

export function questionsPerAttemptLabel(count: number | null | undefined): string | null {
  if (count == null || !Number.isFinite(count) || count < 1) return null
  const n = Math.floor(count)
  return n === 1 ? '1 question per attempt' : `${n} questions per attempt`
}
