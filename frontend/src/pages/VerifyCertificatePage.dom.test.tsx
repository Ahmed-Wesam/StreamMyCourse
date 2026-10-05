/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import VerifyCertificatePage from './VerifyCertificatePage'

const CREDENTIAL_ID = 'RS-ABCDEF-2026-0123456789'

function renderAt(path = '/verify') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/verify" element={<VerifyCertificatePage />} />
        <Route path="/verify/:credentialId" element={<VerifyCertificatePage />} />
      </Routes>
    </MemoryRouter>,
  )
}

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('VerifyCertificatePage', () => {
  const fetchMock = vi.fn()
  const originalEnv = import.meta.env.VITE_API_BASE_URL

  beforeEach(() => {
    fetchMock.mockReset()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = 'https://api.example/v1'
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(import.meta as any).env.VITE_API_BASE_URL = originalEnv
  })

  it('renders the prototype verification heading and credential form', () => {
    renderAt()

    expect(screen.getByRole('heading', { name: /the value of verified credentials/i })).toBeTruthy()
    expect(screen.getByLabelText('Certificate ID')).toBeTruthy()
    expect(screen.getByPlaceholderText('e.g. RS-RM-2026-A1B7F3')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Verify Certificate' })).toBeTruthy()
    expect(screen.queryByText(/demo state/i)).toBeNull()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('looks up a route credential with the public verify client and shows the verified state', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          credentialId: CREDENTIAL_ID,
          status: 'valid',
          studentName: 'Ada Lovelace',
          courseTitle: 'Research Methodology',
          issueDate: 'June 2026',
          instructorName: 'Dr. Bahaa Aburayya',
        },
        200,
      ),
    )

    renderAt(`/verify/${CREDENTIAL_ID}`)

    expect(await screen.findByRole('heading', { name: 'Certificate Verified' })).toBeTruthy()
    expect(screen.getAllByText('Ada Lovelace').length).toBeGreaterThan(0)
    expect(screen.getByText('Study Design Selection')).toBeTruthy()
    expect(screen.getByText(/researchspectrum.org\/verify\/RS-ABCDEF-2026-0123456789/)).toBeTruthy()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(String(url)).toContain(`/certificates/${encodeURIComponent(CREDENTIAL_ID)}`)
    expect(init?.credentials).toBe('omit')
    expect(new Headers(init?.headers).has('Authorization')).toBe(false)
  })

  it('renders not found from a 404 without a student name', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ status: 'not_found', credentialId: 'RS-UNKNOWN-2026-0000000000' }, 404),
    )

    renderAt('/verify/RS-UNKNOWN-2026-0000000000')

    expect(await screen.findByRole('heading', { name: 'Certificate Not Found' })).toBeTruthy()
    expect(screen.getByText('RS-UNKNOWN-2026-0000000000')).toBeTruthy()
    expect(screen.queryByText('Ada Lovelace')).toBeNull()
    expect(screen.queryByText('Competencies Demonstrated')).toBeNull()
  })

  it('renders revoked, expired, and pending states from the API status', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          credentialId: CREDENTIAL_ID,
          status: 'revoked',
          studentName: 'Ada Lovelace',
          courseTitle: 'Statistics & SPSS',
          issueDate: 'January 2025',
          revokedReason: 'Issued in error — superseded by updated credential',
        },
        200,
      ),
    )
    const revoked = renderAt(`/verify/${CREDENTIAL_ID}`)
    expect(await screen.findByRole('heading', { name: 'Certificate Revoked' })).toBeTruthy()
    expect(screen.getByText(/Issued in error — superseded by updated credential/)).toBeTruthy()
    expect(screen.queryByText('Competencies Demonstrated')).toBeNull()
    revoked.unmount()

    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          credentialId: CREDENTIAL_ID,
          status: 'expired',
          studentName: 'Ada Lovelace',
          courseTitle: 'Research Methodology',
          issueDate: 'January 2024',
        },
        200,
      ),
    )
    const expired = renderAt(`/verify/${CREDENTIAL_ID}`)
    expect(await screen.findByRole('heading', { name: 'Certificate Expired' })).toBeTruthy()
    expect(screen.queryByText('Ada Lovelace')).toBeNull()
    expired.unmount()

    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          credentialId: CREDENTIAL_ID,
          status: 'pending',
          studentName: 'Ada Lovelace',
          courseTitle: 'Statistics & SPSS',
          issueDate: 'Processing',
        },
        200,
      ),
    )
    renderAt(`/verify/${CREDENTIAL_ID}`)
    expect(await screen.findByRole('heading', { name: 'Certificate Processing' })).toBeTruthy()
    expect(screen.getByText('Processing')).toBeTruthy()
  })

  it('submits the form through the public verify client', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ status: 'not_found', credentialId: CREDENTIAL_ID }, 404),
    )

    renderAt()
    fireEvent.change(screen.getByLabelText('Certificate ID'), { target: { value: CREDENTIAL_ID } })
    fireEvent.click(screen.getByRole('button', { name: 'Verify Certificate' }))

    expect(await screen.findByRole('heading', { name: 'Certificate Not Found' })).toBeTruthy()
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(`/certificates/${encodeURIComponent(CREDENTIAL_ID)}`)
  })

  it('does not call the API when the credential field is empty', () => {
    renderAt()
    fireEvent.click(screen.getByRole('button', { name: 'Verify Certificate' }))
    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Certificate ID').className).toContain('err')
  })

  it('shows a failed lookup without a verified card', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ message: 'Invalid credential id' }, 400))
    renderAt(`/verify/${CREDENTIAL_ID}`)
    const alert = await screen.findByRole('alert')
    expect(alert.textContent ?? '').toMatch(/failed to verify certificate \(400\)/i)
    expect(screen.queryByRole('heading', { name: 'Certificate Verified' })).toBeNull()
  })
})
