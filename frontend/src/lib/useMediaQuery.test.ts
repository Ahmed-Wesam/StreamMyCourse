/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { readMdUpMatch, useMediaQuery, useIsMdUp } from './useMediaQuery'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('useMediaQuery', () => {
  it('returns fallback when matchMedia is unavailable', () => {
    vi.stubGlobal('matchMedia', undefined)

    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)', true))
    expect(result.current).toBe(true)
  })

  it('subscribes to media query changes', () => {
    let matches = false
    const listeners = new Set<() => void>()
    const mql = {
      get matches() {
        return matches
      },
      addEventListener: (_: string, cb: () => void) => {
        listeners.add(cb)
      },
      removeEventListener: (_: string, cb: () => void) => {
        listeners.delete(cb)
      },
    }
    vi.spyOn(window, 'matchMedia').mockImplementation(() => mql as MediaQueryList)

    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)', false))
    expect(result.current).toBe(false)

    act(() => {
      matches = true
      listeners.forEach((cb) => cb())
    })
    expect(result.current).toBe(true)
  })
})

describe('readMdUpMatch', () => {
  it('returns fallback when matchMedia is unavailable', () => {
    vi.stubGlobal('matchMedia', undefined)
    expect(readMdUpMatch(true)).toBe(true)
    expect(readMdUpMatch(false)).toBe(false)
  })

  it('reads the current md breakpoint match', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation(
      () => ({ matches: true }) as MediaQueryList,
    )
    expect(readMdUpMatch(false)).toBe(true)
  })
})

describe('useIsMdUp', () => {
  it('defaults to desktop layout in tests without matchMedia', () => {
    vi.stubGlobal('matchMedia', undefined)
    const { result } = renderHook(() => useIsMdUp())
    expect(result.current).toBe(true)
  })
})
