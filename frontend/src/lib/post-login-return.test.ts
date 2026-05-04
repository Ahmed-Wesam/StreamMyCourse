import { describe, expect, it } from 'vitest'

import { sanitizeReturnPath } from './post-login-return'

describe('sanitizeReturnPath', () => {
  it('accepts safe relative paths', () => {
    expect(sanitizeReturnPath('/courses/abc?x=1#h')).toBe('/courses/abc?x=1#h')
  })

  it('rejects protocol-relative paths', () => {
    expect(sanitizeReturnPath('//evil.example.com')).toBeNull()
  })

  it('rejects backslashes', () => {
    expect(sanitizeReturnPath('/foo\\bar')).toBeNull()
  })

  it('rejects /login and variants', () => {
    expect(sanitizeReturnPath('/login')).toBeNull()
    expect(sanitizeReturnPath('/login?next=/')).toBeNull()
    expect(sanitizeReturnPath('/login#x')).toBeNull()
  })
})
