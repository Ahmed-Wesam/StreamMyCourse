/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import FaqPage from './FaqPage'

function renderFaq() {
  return render(
    <MemoryRouter>
      <FaqPage />
    </MemoryRouter>,
  )
}

describe('FaqPage', () => {
  afterEach(() => {
    cleanup()
  })

  it('opens accordion questions independently without closing others', () => {
    renderFaq()

    const buttons = screen.getAllByRole('button').filter((btn) =>
      btn.hasAttribute('aria-expanded'),
    )
    expect(buttons.length).toBeGreaterThanOrEqual(2)

    const first = buttons[0]
    const second = buttons[1]
    expect(first.getAttribute('aria-expanded')).toBe('false')
    expect(second.getAttribute('aria-expanded')).toBe('false')

    fireEvent.click(first)
    expect(first.getAttribute('aria-expanded')).toBe('true')
    const firstControls = first.getAttribute('aria-controls')
    expect(firstControls).toBeTruthy()
    const firstPanel = document.getElementById(firstControls!)
    expect(firstPanel).toBeTruthy()
    expect((firstPanel!.textContent ?? '').trim().length).toBeGreaterThan(0)
    expect(firstPanel!.textContent).toMatch(/\S/)

    fireEvent.click(second)
    expect(second.getAttribute('aria-expanded')).toBe('true')
    expect(first.getAttribute('aria-expanded')).toBe('true')
    const secondControls = second.getAttribute('aria-controls')
    expect(secondControls).toBeTruthy()
    const secondPanel = document.getElementById(secondControls!)
    expect(secondPanel).toBeTruthy()
    expect((secondPanel!.textContent ?? '').trim().length).toBeGreaterThan(0)
  })
})
