import { describe, expect, it } from 'vitest'

import { privacyEn } from './privacy.en'

function privacyText(): string {
  return [
    privacyEn.title,
    ...privacyEn.sections.flatMap((section) => [section.heading, ...section.paragraphs]),
  ].join('\n')
}

describe('privacy.en contract', () => {
  it('mentions shipped personal and educational data categories', () => {
    const text = privacyText()

    expect(text).toMatch(/profession/i)
    expect(text).toMatch(/purchase/i)
    expect(text).toMatch(/notes|lesson uploads?/i)
    expect(text).toMatch(/Research Team application|application PII/i)
  })

  it('does not invent Certificate Visibility Controls', () => {
    expect(privacyText()).not.toMatch(/Certificate Visibility Controls/i)
  })
})
