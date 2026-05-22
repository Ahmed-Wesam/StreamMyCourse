/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { RouteChunkFallback } from './RouteChunkFallback'

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
})
