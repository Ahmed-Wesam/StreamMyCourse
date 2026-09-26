/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Badge } from './Badge'

describe('Badge', () => {
  afterEach(() => {
    cleanup()
  })

  it.each([
    ['neutral', 'Draft'] as const,
    ['blue', 'Featured'] as const,
    ['success', 'Owned'] as const,
  ])('renders label for tone %s', (tone, label) => {
    render(<Badge tone={tone}>{label}</Badge>)
    expect(screen.getByText(label)).toBeTruthy()
  })
})
