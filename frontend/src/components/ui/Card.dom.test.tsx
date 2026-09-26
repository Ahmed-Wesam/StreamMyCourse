/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Card } from './Card'

describe('Card', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders children and appends className', () => {
    const { container } = render(
      <Card className="extra-card-class" data-testid="card">
        <p>Card body</p>
      </Card>,
    )

    expect(screen.getByText('Card body')).toBeTruthy()
    const el = screen.getByTestId('card')
    expect(el.className).toMatch(/extra-card-class/)
    expect(container.firstElementChild).toBe(el)
  })
})
