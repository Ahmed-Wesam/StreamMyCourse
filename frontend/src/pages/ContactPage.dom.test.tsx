/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { legalConfig } from '../lib/legalConfig'
import { contactFormCopy } from '../lib/marketing/contactCopy'
import ContactPage from './ContactPage'

function renderContact() {
  return render(
    <MemoryRouter>
      <ContactPage />
    </MemoryRouter>,
  )
}

function fillValidContactForm() {
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
}

describe('ContactPage', () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  const fetchMock = vi.fn()
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    writeText.mockClear()
    fetchMock.mockClear()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
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

  it('does not render a file input', () => {
    renderContact()

    expect(document.querySelector('input[type="file"]')).toBeNull()
  })

  it('links the Instagram card to the Research Spectrum profile', () => {
    renderContact()

    const link = screen.getByRole('link', { name: /visit instagram/i })
    expect(link.getAttribute('href')).toBe('https://www.instagram.com/researchspectrum/')
  })

  it('shows a WhatsApp Coming Soon control that is not a wa.me link', () => {
    renderContact()

    const control = screen.getByText('Coming Soon')
    expect(control.closest('a')).toBeNull()
    expect(control.getAttribute('href')).toBeNull()
    expect(document.querySelector('a[href*="wa.me"]')).toBeNull()
  })

  it('valid submit POSTs JSON to /contact once without Authorization', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ accepted: true }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    renderContact()
    fillValidContactForm()
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(String(url)).toMatch(/\/contact$/)
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('omit')
    const headers = new Headers(init.headers)
    expect(headers.get('Content-Type')).toBe('application/json')
    expect(headers.has('Authorization')).toBe(false)
    expect(JSON.parse(String(init.body))).toEqual({
      name: 'Ada Lovelace',
      email: 'ada@example.com',
      category: 'General Question',
      subject: 'Hello',
      message: 'This is a long enough contact message for support.',
    })
  })

  it('shows success copy on 202 and does not echo the message body', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ accepted: true }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    renderContact()
    fillValidContactForm()
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    const status = await screen.findByRole('status')
    expect(status.textContent).toBe(contactFormCopy.successStatus)
    expect(document.body.textContent).not.toContain(
      'This is a long enough contact message for support.',
    )
  })

  it.each([
    [400, contactFormCopy.validationErrorStatus],
    [429, contactFormCopy.rateLimitStatus],
    [503, contactFormCopy.unavailableStatus],
  ] as const)('shows error status copy on HTTP %s (not success)', async (httpStatus, expectedCopy) => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ message: 'server detail' }), {
        status: httpStatus,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    renderContact()
    fillValidContactForm()
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    const status = await screen.findByRole('status')
    expect(status.textContent).toBe(expectedCopy)
    expect(status.textContent).not.toBe(contactFormCopy.successStatus)
    expect(document.body.textContent).not.toContain('server detail')
  })
})
