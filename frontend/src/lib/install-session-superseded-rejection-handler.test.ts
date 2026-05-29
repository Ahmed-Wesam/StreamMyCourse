/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

const notifySessionSupersededMock = vi.hoisted(() => vi.fn())

vi.mock('./handleSessionSuperseded', () => ({
  notifySessionSuperseded: (...args: unknown[]) => notifySessionSupersededMock(...args),
}))

import {
  installSessionSupersededRejectionHandler,
  resetSessionSupersededRejectionHandlerForTests,
} from './install-session-superseded-rejection-handler'

describe('installSessionSupersededRejectionHandler', () => {
  afterEach(() => {
    resetSessionSupersededRejectionHandlerForTests()
    notifySessionSupersededMock.mockClear()
  })

  it('notifies on unhandled rejection with Cognito stale refresh message', () => {
    installSessionSupersededRejectionHandler()
    const reason = new Error(
      'student refresh session superseded (client_metadata_session_id_vs_rds_active)',
    )
    const promise = Promise.reject(reason)
    void promise.catch(() => {})
    window.dispatchEvent(
      new PromiseRejectionEvent('unhandledrejection', { promise, reason }),
    )
    expect(notifySessionSupersededMock).toHaveBeenCalledTimes(1)
  })

  it('ignores unrelated unhandled rejections', () => {
    installSessionSupersededRejectionHandler()
    const reason = new Error('something else')
    const promise = Promise.reject(reason)
    void promise.catch(() => {})
    window.dispatchEvent(
      new PromiseRejectionEvent('unhandledrejection', { promise, reason }),
    )
    expect(notifySessionSupersededMock).not.toHaveBeenCalled()
  })
})
