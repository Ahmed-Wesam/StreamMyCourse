/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest'

import {
  clearSessionSupersededBanner,
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
  SESSION_SUPERSEDED_BANNER_KEY,
} from './session-superseded-banner'

describe('session-superseded-banner', () => {
  afterEach(() => {
    sessionStorage.clear()
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
})
