/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { legalConfig } from '../lib/legalConfig'
import ContactPage from './ContactPage'

function renderContact() {
  return render(
    <MemoryRouter>
      <ContactPage />
    </MemoryRouter>,
  )
}

describe('ContactPage', () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  const fetchMock = vi.fn()

  beforeEach(() => {
    writeText.mockClear()
    fetchMock.mockClear()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('copy control writes legalConfig.supportEmail only', async () => {
    renderContact()

    fireEvent.click(screen.getByRole('button', { name: /copy email/i }))

    expect(writeText).toHaveBeenCalledTimes(1)
    expect(writeText).toHaveBeenCalledWith(legalConfig.supportEmail)
  })

  it('mailto href uses support email and excludes form field values', () => {
    renderContact()

    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: 'Injected\r\nBcc: evil@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: 'attacker@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/^subject$/i), {
      target: { value: 'Subject header injection' },
    })
    fireEvent.change(screen.getByLabelText(/^message$/i), {
      target: { value: 'Message body that must not appear in mailto' },
    })

    const mailtoLinks = screen
      .getAllByRole('link')
      .filter((el) => (el.getAttribute('href') ?? '').startsWith('mailto:'))
    expect(mailtoLinks.length).toBeGreaterThan(0)
    for (const mailto of mailtoLinks) {
      const href = mailto.getAttribute('href') ?? ''
      expect(href).toBe(`mailto:${legalConfig.supportEmail}`)
      expect(href).not.toContain('Injected')
      expect(href).not.toContain('attacker@example.com')
      expect(href).not.toContain('Subject header')
      expect(href).not.toContain('Message body')
    }
  })

  it('submit does not call fetch and shows messaging is not available yet', () => {
    renderContact()

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Ada Lovelace' } })
    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: 'ada@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/subject category/i), {
      target: { value: 'General Question' },
    })
    fireEvent.change(screen.getByLabelText(/^subject$/i), { target: { value: 'Hello' } })
    fireEvent.change(screen.getByLabelText(/^message$/i), {
      target: { value: 'This is a long enough contact message for support.' },
    })

    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    expect(fetchMock).not.toHaveBeenCalled()
    const status = screen.getByRole('status')
    expect(status.textContent).toMatch(/messaging is not available yet/i)
    expect(status.className).not.toMatch(/fef2f2|b91c1c|fecaca/)
    expect(document.body.textContent).toMatch(/email support/i)
  })

  it('file input is disabled', () => {
    renderContact()

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null
    expect(fileInput).toBeTruthy()
    expect(fileInput!.disabled).toBe(true)
  })
})
