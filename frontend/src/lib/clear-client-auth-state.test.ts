/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest'

import { clearClientAuthState } from './clear-client-auth-state'
import {
  enterSupersededState,
  isStudentSessionSuperseded,
  resetStudentSessionSupersededForTests,
} from './student-session-superseded'
import {
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
  SESSION_SUPERSEDED_BANNER_KEY,
} from './session-superseded-banner'

describe('clearClientAuthState', () => {
  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    document.cookie = ''
    resetStudentSessionSupersededForTests()
  })

  it('clears localStorage and best-effort document cookies', () => {
    localStorage.setItem('t', '1')
    document.cookie = 'a=b'
    clearClientAuthState()
    expect(localStorage.getItem('t')).toBeNull()
    expect(document.cookie).not.toMatch(/a=b/)
  })

  it('preserves session-superseded banner in sessionStorage by default', () => {
    persistSessionSupersededBanner('Signed in elsewhere')
    clearClientAuthState()
    expect(sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)).toBe('Signed in elsewhere')
    expect(readSessionSupersededBanner()).toBe('Signed in elsewhere')
  })

  it('clears session-superseded banner when clearSupersededBanner is true', () => {
    persistSessionSupersededBanner('Signed in elsewhere')
    clearClientAuthState({ clearSupersededBanner: true })
    expect(sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)).toBeNull()
  })

  it('preserves supersede state during supersede storage wipe', () => {
    persistSessionSupersededBanner('Signed in elsewhere')
    enterSupersededState()
    clearClientAuthState()
    expect(isStudentSessionSuperseded()).toBe(true)
  })

  it('clears supersede state when clearSupersededBanner is true', () => {
    enterSupersededState()
    clearClientAuthState({ clearSupersededBanner: true })
    expect(isStudentSessionSuperseded()).toBe(false)
  })
})
