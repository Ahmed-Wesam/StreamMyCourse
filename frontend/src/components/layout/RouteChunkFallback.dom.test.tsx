/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { RouteChunkFallback } from './RouteChunkFallback'

const FORBIDDEN_CLASS_SUBSTRINGS = ['emerald-', 'slate-'] as const

function collectClassNames(root: Element): string[] {
  const names: string[] = []
  const walk = (el: Element) => {
    if (typeof el.className === 'string' && el.className.length > 0) {
      names.push(el.className)
    }
    for (const child of el.children) {
      walk(child)
    }
  }
  walk(root)
  return names
}

function findForbiddenPaletteClasses(classNames: string[]): string[] {
  const hits: string[] = []
  for (const cn of classNames) {
    for (const forbidden of FORBIDDEN_CLASS_SUBSTRINGS) {
      if (cn.includes(forbidden)) {
        hits.push(`${forbidden} → ${cn}`)
      }
    }
  }
  return hits
}

describe('RouteChunkFallback', () => {
  afterEach(() => {
    cleanup()
  })

  it('exposes accessible status region with loading copy', () => {
    render(<RouteChunkFallback />)

    const status = screen.getByRole('status')
    expect(status.getAttribute('aria-live')).toBe('polite')
    expect(screen.getByText('Loading…')).toBeTruthy()
  })

  it('uses RS palette on the full fallback card (no emerald or slate utilities)', () => {
    render(<RouteChunkFallback />)

    const status = screen.getByRole('status')
    const violations = findForbiddenPaletteClasses(collectClassNames(status))
    expect(violations).toEqual([])
  })
})
