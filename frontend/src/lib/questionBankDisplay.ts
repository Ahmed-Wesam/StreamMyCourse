import type { QuestionBankSummary } from './api'

export function questionBankDisplayName(bank: Pick<QuestionBankSummary, 'questionBankId' | 'name'>): string {
  const name = typeof bank.name === 'string' ? bank.name.trim() : ''
  return name || bank.questionBankId
}

export function questionBankIdLabel(questionBankId: string): string {
  return `ID: ${questionBankId}`
}
