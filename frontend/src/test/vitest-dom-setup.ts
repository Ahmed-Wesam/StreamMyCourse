/**
 * React Router 7 client navigations in Vitest/jsdom use undici Request, which rejects
 * jsdom AbortSignal instances. Strip navigation signals in tests only (no production impact).
 */
import { beforeAll } from 'vitest'

beforeAll(() => {
  if (typeof document === 'undefined') return

  // jsdom does not implement matchMedia. Vitest 5 no longer adds a spyable stub,
  // and vi.spyOn(window, 'matchMedia') throws when the property is missing.
  if (typeof window.matchMedia !== 'function') {
    window.matchMedia = (query: string) =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as MediaQueryList
  }

  const NativeRequest = globalThis.Request
  class PatchedRequest extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      if (init?.signal) {
        const { signal, ...restInit } = init
        void signal
        super(input, restInit)
        return
      }
      super(input, init)
    }
  }
  globalThis.Request = PatchedRequest as typeof Request
})
