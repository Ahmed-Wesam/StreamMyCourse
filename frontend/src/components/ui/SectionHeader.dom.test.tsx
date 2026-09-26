/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { SectionHeader } from './SectionHeader'

describe('SectionHeader', () => {
  afterEach(() => {
    cleanup()
  })

  it('heading uses the requested level', () => {
    const { rerender } = render(<SectionHeader title="Alpha" level={1} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Alpha' })).toBeTruthy()

    rerender(<SectionHeader title="Beta" level={2} />)
    expect(screen.getByRole('heading', { level: 2, name: 'Beta' })).toBeTruthy()

    rerender(<SectionHeader title="Gamma" level={3} />)
    expect(screen.getByRole('heading', { level: 3, name: 'Gamma' })).toBeTruthy()
  })

  it('lead is absent when omitted and present when passed', () => {
    const { rerender } = render(<SectionHeader title="Courses" />)
    expect(screen.queryByText(/sharpen one skill/i)).toBeNull()

    rerender(
      <SectionHeader title="Courses" lead="Take a single course to sharpen one skill." />,
    )
    expect(screen.getByText('Take a single course to sharpen one skill.')).toBeTruthy()
  })

  it('kicker text shows when passed', () => {
    render(<SectionHeader kicker="Learn with us" title="Programs" />)
    expect(screen.getByText('Learn with us')).toBeTruthy()
  })
})
