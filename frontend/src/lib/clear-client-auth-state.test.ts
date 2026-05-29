/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest'

import { clearClientAuthState } from './clear-client-auth-state'

describe('clearClientAuthState', () => {
  afterEach(() => {
    localStorage.clear()
    document.cookie = ''
  })

  it('clears localStorage and best-effort document cookies', () => {
    localStorage.setItem('t', '1')
    document.cookie = 'a=b'
    clearClientAuthState()
    expect(localStorage.getItem('t')).toBeNull()
    expect(document.cookie).not.toMatch(/a=b/)
  })
})
