/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { Button } from './Button'

describe('Button', () => {
  afterEach(() => {
    cleanup()
  })

  it('default element is button with type="button"', () => {
    render(<Button>Continue</Button>)
    const el = screen.getByRole('button', { name: 'Continue' })
    expect(el.tagName).toBe('BUTTON')
    expect(el.getAttribute('type')).toBe('button')
  })

  it('to renders a link to that path', () => {
    render(
      <MemoryRouter>
        <Button to="/courses">Browse</Button>
      </MemoryRouter>,
    )
    const el = screen.getByRole('link', { name: 'Browse' })
    expect(el.getAttribute('href')).toBe('/courses')
  })

  it('href renders an anchor', () => {
    render(<Button href="https://example.com">External</Button>)
    const el = screen.getByRole('link', { name: 'External' })
    expect(el.tagName).toBe('A')
    expect(el.getAttribute('href')).toBe('https://example.com')
  })

  it('disabled is exposed to assistive tech', () => {
    const { rerender } = render(<Button disabled>Save</Button>)
    const button = screen.getByRole('button', { name: 'Save' })
    expect(button.hasAttribute('disabled') || button.getAttribute('aria-disabled') === 'true').toBe(
      true,
    )

    rerender(
      <MemoryRouter>
        <Button to="/account" disabled>
          Account
        </Button>
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: 'Account' })
    expect(link.getAttribute('aria-disabled')).toBe('true')
  })

  it('onDark clears the primary gradient so white fill can show on blue bands', () => {
    render(<Button variant="onDark">Explore courses</Button>)
    const el = screen.getByRole('button', { name: 'Explore courses' })
    expect(el.className).toMatch(/\brs-btn-on-dark\b/)
    expect(el.className).not.toMatch(/\brs-btn-primary\b/)
  })

  it('ghostOnDark uses the on-dark outline class instead of light ghost', () => {
    render(<Button variant="ghostOnDark">Learn More</Button>)
    const el = screen.getByRole('button', { name: 'Learn More' })
    expect(el.className).toMatch(/\brs-btn-ghost-on-dark\b/)
    expect(el.className.split(/\s+/)).not.toContain('rs-btn-ghost')
  })
})
