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
    expect(text).toMatch(/lesson notes/i)
    expect(text).toMatch(/assignment submission/i)
    expect(text).not.toMatch(/Lesson uploads and other course materials you submit/i)
    expect(text).not.toMatch(/Examination results/i)
    expect(text).not.toMatch(/QR verification data/i)
    expect(text).not.toMatch(/Maximum registered device limits/i)
    expect(text).not.toMatch(/Learning management systems/i)
    expect(text).not.toMatch(/unsubscribe from marketing communications at any time/i)
    expect(text).not.toMatch(/• Phone number/i)
    expect(text).toMatch(/Single-session|session/i)
    expect(text).toMatch(/Research Team application|application PII/i)
    expect(text).not.toMatch(/account deletion through the platform's account settings/i)
  })

  it('does not invent Certificate Visibility Controls', () => {
    expect(privacyText()).not.toMatch(/Certificate Visibility Controls/i)
  })
})
