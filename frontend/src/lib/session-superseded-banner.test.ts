/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  enterSupersededState,
  isStudentSessionSuperseded,
  resetStudentSessionSupersededForTests,
} from './student-session-superseded'
import {
  clearSessionSupersededBanner,
  dismissSessionSupersededBannerUi,
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
  resetSessionSupersededDismissListenersForTests,
  SESSION_SUPERSEDED_BANNER_KEY,
  subscribeSessionSupersededDismiss,
} from './session-superseded-banner'

describe('session-superseded-banner', () => {
  afterEach(() => {
    sessionStorage.clear()
    resetSessionSupersededDismissListenersForTests()
    resetStudentSessionSupersededForTests()
  })

  it('persists and reads the supersede message', () => {
    persistSessionSupersededBanner('Signed in elsewhere')
    expect(sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)).toBe('Signed in elsewhere')
    expect(readSessionSupersededBanner()).toBe('Signed in elsewhere')
  })

  it('returns null for empty or whitespace-only stored values', () => {
    sessionStorage.setItem(SESSION_SUPERSEDED_BANNER_KEY, '   ')
    expect(readSessionSupersededBanner()).toBeNull()
  })

  it('clears the stored message', () => {
    persistSessionSupersededBanner('msg')
    clearSessionSupersededBanner()
    expect(readSessionSupersededBanner()).toBeNull()
  })

  it('dismissSessionSupersededBannerUi clears storage, supersede state, and notifies listeners', () => {
    const listener = vi.fn()
    persistSessionSupersededBanner('Signed in elsewhere')
    enterSupersededState()
    const unsubscribe = subscribeSessionSupersededDismiss(listener)

    dismissSessionSupersededBannerUi()
    unsubscribe()

    expect(readSessionSupersededBanner()).toBeNull()
    expect(isStudentSessionSuperseded()).toBe(false)
    expect(listener).toHaveBeenCalledTimes(1)
  })
})
