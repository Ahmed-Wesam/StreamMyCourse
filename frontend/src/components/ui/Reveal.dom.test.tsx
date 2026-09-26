/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { Reveal } from './Reveal'

type FakeIOInstance = {
  disconnected?: boolean
  observe: () => void
  disconnect: () => void
}

describe('Reveal', () => {
  let observerCallback: IntersectionObserverCallback | undefined
  let instances: FakeIOInstance[]
  let OriginalIO: typeof IntersectionObserver | undefined
  let OriginalMatchMedia: typeof window.matchMedia | undefined

  beforeEach(() => {
    observerCallback = undefined
    instances = []
    OriginalIO = window.IntersectionObserver
    OriginalMatchMedia = window.matchMedia
  })

  afterEach(() => {
    cleanup()
    if (OriginalIO) {
      window.IntersectionObserver = OriginalIO
    } else {
      delete (window as { IntersectionObserver?: typeof IntersectionObserver }).IntersectionObserver
    }
    if (OriginalMatchMedia) {
      window.matchMedia = OriginalMatchMedia
    }
    vi.restoreAllMocks()
  })

  function stubMatchMedia(reduced: boolean) {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: reduced && query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
  }

  function installFakeIO() {
    class IO {
      disconnected = false
      constructor(fn: IntersectionObserverCallback) {
        observerCallback = fn
        instances.push(this)
      }
      observe() {}
      disconnect() {
        this.disconnected = true
      }
    }
    window.IntersectionObserver = IO as unknown as typeof IntersectionObserver
  }

  it('reduced motion: visible immediately (in class) and no observer constructed', () => {
    stubMatchMedia(true)
    installFakeIO()

    const { container } = render(
      <Reveal>
        <p>Animated</p>
      </Reveal>,
    )

    expect(screen.getByText('Animated')).toBeTruthy()
    expect(container.firstElementChild?.classList.contains('in')).toBe(true)
    expect(instances).toHaveLength(0)
  })

  it('observer missing: in present immediately', () => {
    stubMatchMedia(false)
    delete (window as { IntersectionObserver?: typeof IntersectionObserver }).IntersectionObserver

    const { container } = render(
      <Reveal>
        <p>Fallback</p>
      </Reveal>,
    )

    expect(container.firstElementChild?.classList.contains('in')).toBe(true)
  })

  it('when observer fires: in is added', async () => {
    stubMatchMedia(false)
    installFakeIO()

    const { container } = render(
      <Reveal>
        <p>Reveal me</p>
      </Reveal>,
    )

    const wrap = container.firstElementChild
    expect(wrap?.classList.contains('in')).toBe(false)
    expect(instances).toHaveLength(1)
    expect(observerCallback).toBeTypeOf('function')

    observerCallback!(
      [{ isIntersecting: true } as IntersectionObserverEntry],
      instances[0] as unknown as IntersectionObserver,
    )

    await waitFor(() => {
      expect(wrap?.classList.contains('in')).toBe(true)
    })
  })

  it('unmount disconnects the observer', () => {
    stubMatchMedia(false)
    installFakeIO()

    const { unmount } = render(
      <Reveal>
        <p>Leave</p>
      </Reveal>,
    )

    expect(instances).toHaveLength(1)
    unmount()
    expect(instances[0]?.disconnected).toBe(true)
  })
})
