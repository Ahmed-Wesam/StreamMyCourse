import { describe, expect, it } from 'vitest'

import { formatModuleQuizQuestionCount, quizScorePercentPillClass } from './quizScoreDisplay'

describe('quizScorePercentPillClass', () => {
  it('uses red styling below 50%', () => {
    expect(quizScorePercentPillClass(49)).toContain('bg-red-100')
    expect(quizScorePercentPillClass(0)).toContain('text-red-700')
  })

  it('uses yellow styling from 50% up to below 75%', () => {
    expect(quizScorePercentPillClass(50)).toContain('bg-amber-100')
    expect(quizScorePercentPillClass(74)).toContain('text-amber-800')
  })

  it('uses green styling at 75% and above', () => {
    expect(quizScorePercentPillClass(75)).toContain('bg-emerald-100')
    expect(quizScorePercentPillClass(100)).toContain('text-emerald-700')
  })
})

describe('formatModuleQuizQuestionCount', () => {
  it('uses singular for one question', () => {
    expect(formatModuleQuizQuestionCount(1)).toBe('1 question')
  })

  it('uses plural for multiple questions', () => {
    expect(formatModuleQuizQuestionCount(3)).toBe('3 questions')
  })
})
