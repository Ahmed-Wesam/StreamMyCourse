/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest'

import { clearClientAuthState } from './clear-client-auth-state'
import {
  armSessionSupersedeHandling,
  isSessionSupersedeHandling,
  resetSessionSupersedeHandlingForTests,
} from './session-supersede-handling'
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
    resetSessionSupersedeHandlingForTests()
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

  it('preserves supersede latch during supersede storage wipe', () => {
    persistSessionSupersededBanner('Signed in elsewhere')
    armSessionSupersedeHandling()
    clearClientAuthState()
    expect(isSessionSupersedeHandling()).toBe(true)
  })

  it('clears supersede latch when clearSupersededBanner is true', () => {
    armSessionSupersedeHandling()
    clearClientAuthState({ clearSupersededBanner: true })
    expect(isSessionSupersedeHandling()).toBe(false)
  })
})
