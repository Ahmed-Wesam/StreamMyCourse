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

function openFaqAnswer(question: RegExp): string {
  const button = screen.getByRole('button', { name: question })
  fireEvent.click(button)
  const panelId = button.getAttribute('aria-controls')
  expect(panelId).toBeTruthy()
  const panel = document.getElementById(panelId!)
  expect(panel).toBeTruthy()
  return panel!.textContent ?? ''
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

  it('does not invent Settings notification or privacy preference pages', () => {
    renderFaq()

    const notification = openFaqAnswer(/How do notification settings work\?/i)
    expect(notification).not.toMatch(/Settings page/i)
    expect(notification).toMatch(/Account|email|Contact/i)

    const privacy = openFaqAnswer(/Can I manage my privacy settings\?/i)
    expect(privacy).not.toMatch(/Settings page/i)
    expect(privacy).toMatch(/Privacy Policy/i)
  })

  it('does not invent a Certificate Eligible stage before issuance', () => {
    renderFaq()

    const answer = openFaqAnswer(/What does ["']?certificate eligibility["']? mean\?/i)
    expect(answer).not.toMatch(/Certificate Eligible/i)
    expect(answer).not.toMatch(/stage just before certificate issuance/i)
    expect(answer).toMatch(/quiz|assignment|certificate/i)
  })

  it('points Research Team eligibility at the live required list, not interviews or hard-coded all-four certificates', () => {
    renderFaq()

    const whoCanApply = openFaqAnswer(/Who can apply for the Research Team\?/i)
    expect(whoCanApply).not.toMatch(/all four certificates are required/i)
    expect(whoCanApply).not.toMatch(/interview/i)
    expect(whoCanApply).toMatch(/\/research-team|Research Team page|admin/i)
    expect(whoCanApply).toMatch(/required course/i)

    const selected = openFaqAnswer(/How are Research Team applicants selected\?/i)
    expect(selected).not.toMatch(/\binterviews?\b/i)
    expect(selected).not.toMatch(/brief interview/i)
    expect(selected).toMatch(/assignment|performance|skill/i)

    const bundle = openFaqAnswer(/Can I purchase courses individually/i)
    expect(bundle).not.toMatch(/all four certificates are required for eligibility/i)
    expect(bundle).toMatch(/\/research-team|Research Team page/i)
  })
})
