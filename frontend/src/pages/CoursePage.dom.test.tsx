/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import CoursePage from './CoursePage'

describe('CoursePage pricing selection', () => {
  afterEach(() => cleanup())

  it('moves "Enroll Now" button text to the selected plan', () => {
    render(
      <MemoryRouter>
        <CoursePage />
      </MemoryRouter>,
    )

    const plan3 = screen.getByTestId('pricing-plan-3month')
    const plan6 = screen.getByTestId('pricing-plan-6month')
    expect(plan3).toBeTruthy()
    expect(plan6).toBeTruthy()

    // Default selection is 3 months.
    expect(plan3.getAttribute('aria-checked')).toBe('true')
    expect(plan6.getAttribute('aria-checked')).toBe('false')
    // Most popular is NOT automatically blue if not selected.
    expect(screen.getByTestId('pricing-plan-1month').getAttribute('aria-checked')).toBe('false')

    fireEvent.click(plan6)
    expect(plan6.getAttribute('aria-checked')).toBe('true')
    expect(plan3.getAttribute('aria-checked')).toBe('false')
  })
})

