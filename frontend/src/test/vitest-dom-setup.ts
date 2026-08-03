/**
 * React Router 7 client navigations in Vitest/jsdom use undici Request, which rejects
 * jsdom AbortSignal instances. Strip navigation signals in tests only (no production impact).
 */
import { beforeAll } from 'vitest'

beforeAll(() => {
  if (typeof document === 'undefined') return

  const NativeRequest = globalThis.Request
  class PatchedRequest extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      if (init?.signal) {
        const { signal: _signal, ...restInit } = init
        super(input, restInit)
        return
      }
      super(input, init)
    }
  }
  globalThis.Request = PatchedRequest as typeof Request
})
