/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

import { sessionSupersededUserMessage } from './apiUserMessages'
import * as amplifyCaches from './clear-amplify-auth-caches'
import * as banner from './session-superseded-banner-storage'
import {
  enterSupersededState,
  exitSupersededState,
  isStudentSessionSuperseded,
  notifySessionSuperseded,
  resetSessionSupersededNotifyCooldownForTests,
  resetStudentSessionSupersededForTests,
  subscribeSessionSuperseded,
  syncSupersededFromStorage,
} from './student-session-superseded'
import {
  installSessionSupersededRejectionHandler,
  resetSessionSupersededRejectionHandlerForTests,
} from './install-session-superseded-rejection-handler'
import {
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
  SESSION_SUPERSEDED_BANNER_KEY,
} from './session-superseded-banner'

describe('student-session-superseded', () => {
  afterEach(() => {
    sessionStorage.clear()
    resetStudentSessionSupersededForTests()
    resetSessionSupersededNotifyCooldownForTests()
    resetSessionSupersededRejectionHandlerForTests()
  })

  it('enterSupersededState twice persists banner once and sets in-memory flag', () => {
    const persistSpy = vi.spyOn(banner, 'persistSessionSupersededBanner')

    enterSupersededState()
    enterSupersededState()

    expect(persistSpy).toHaveBeenCalledTimes(1)
    expect(persistSpy).toHaveBeenCalledWith(sessionSupersededUserMessage)
    expect(readSessionSupersededBanner()).toBe(sessionSupersededUserMessage)
    expect(isStudentSessionSuperseded()).toBe(true)

    persistSpy.mockRestore()
  })

  it('notifySessionSuperseded twice within cooldown invokes listener once', () => {
    const listener = vi.fn()
    const unsubscribe = subscribeSessionSuperseded(listener)

    notifySessionSuperseded()
    notifySessionSuperseded()

    expect(listener).toHaveBeenCalledTimes(1)
    unsubscribe()
  })

  it('notifySessionSuperseded does not wipe Amplify auth caches', () => {
    const clearCachesSpy = vi.spyOn(amplifyCaches, 'clearAmplifyAuthCaches')

    notifySessionSuperseded()
    notifySessionSuperseded()

    expect(clearCachesSpy).not.toHaveBeenCalled()
    clearCachesSpy.mockRestore()
  })

  it('syncSupersededFromStorage with persisted banner sets flag without invoking listeners', () => {
    persistSessionSupersededBanner(sessionSupersededUserMessage)
    const listener = vi.fn()
    const unsubscribe = subscribeSessionSuperseded(listener)

    syncSupersededFromStorage()

    expect(isStudentSessionSuperseded()).toBe(true)
    expect(listener).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('exitSupersededState clears in-memory flag and stored banner', () => {
    enterSupersededState()

    expect(isStudentSessionSuperseded()).toBe(true)
    expect(readSessionSupersededBanner()).toBe(sessionSupersededUserMessage)

    exitSupersededState()

    expect(isStudentSessionSuperseded()).toBe(false)
    expect(readSessionSupersededBanner()).toBeNull()
    expect(sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)).toBeNull()
  })

  describe('installSessionSupersededRejectionHandler', () => {
    it('notifies on unhandled rejection with Cognito stale refresh message', () => {
      const listener = vi.fn()
      const unsubscribe = subscribeSessionSuperseded(listener)
      installSessionSupersededRejectionHandler()

      const reason = new Error(
        'student refresh session superseded (client_metadata_session_id_vs_rds_active)',
      )
      const promise = Promise.reject(reason)
      void promise.catch(() => {})
      window.dispatchEvent(
        new PromiseRejectionEvent('unhandledrejection', { promise, reason }),
      )

      expect(listener).toHaveBeenCalledTimes(1)
      unsubscribe()
    })

    it('ignores unrelated unhandled rejections', () => {
      const listener = vi.fn()
      const unsubscribe = subscribeSessionSuperseded(listener)
      installSessionSupersededRejectionHandler()

      const reason = new Error('something else')
      const promise = Promise.reject(reason)
      void promise.catch(() => {})
      window.dispatchEvent(
        new PromiseRejectionEvent('unhandledrejection', { promise, reason }),
      )

      expect(listener).not.toHaveBeenCalled()
      unsubscribe()
    })
  })
})
