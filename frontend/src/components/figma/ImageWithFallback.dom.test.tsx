/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImageWithFallback } from './ImageWithFallback'

describe('ImageWithFallback', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders the provided src initially', () => {
    render(<ImageWithFallback alt="avatar" src="/primary.png" />)
    const img = screen.getByRole('img', { name: /avatar/i }) as HTMLImageElement
    expect(img.getAttribute('src')).toBe('/primary.png')
  })

  it('switches to fallback src on error (only once)', () => {
    render(<ImageWithFallback alt="avatar" src="/primary.png" fallbackSrc="/fallback.png" />)
    const img = screen.getByRole('img', { name: /avatar/i }) as HTMLImageElement

    fireEvent.error(img)
    expect(img.getAttribute('src')).toBe('/fallback.png')

    // Second error should not flip-flop or re-set state unnecessarily.
    fireEvent.error(img)
    expect(img.getAttribute('src')).toBe('/fallback.png')
  })

  it('invokes the consumer onError handler', () => {
    const onError = vi.fn()
    render(<ImageWithFallback alt="avatar" src="/primary.png" fallbackSrc="/fallback.png" onError={onError} />)
    const img = screen.getByRole('img', { name: /avatar/i })
    fireEvent.error(img)
    expect(onError).toHaveBeenCalledTimes(1)
  })
})

