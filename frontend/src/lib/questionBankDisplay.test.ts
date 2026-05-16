import { describe, expect, it } from 'vitest'

import { questionsPerAttemptLabel, questionBankStatusLabel } from './questionBankDisplay'

describe('questionBankDisplay', () => {
  it('formats status labels for instructors', () => {
    expect(questionBankStatusLabel('DRAFT')).toBe('Draft')
    expect(questionBankStatusLabel('PUBLISHED')).toBe('Published')
  })

  it('formats questions per attempt', () => {
    expect(questionsPerAttemptLabel(null)).toBeNull()
    expect(questionsPerAttemptLabel(1)).toBe('1 question per attempt')
    expect(questionsPerAttemptLabel(5)).toBe('5 questions per attempt')
  })
})
