/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const hasSignedInMock = vi.hoisted(() => vi.fn())
const fetchMeMock = vi.hoisted(() => vi.fn())

vi.mock('../../lib/api/session', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api/session')>()
  return {
    ...actual,
    hasSignedInIdToken: (...args: unknown[]) => hasSignedInMock(...args),
    fetchMe: (...args: unknown[]) => fetchMeMock(...args),
  }
})

import { StudentTermsGate } from './StudentTermsGate'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <StudentTermsGate>
        <Routes>
          <Route path="/courses" element={<div>Courses</div>} />
          <Route path="/account/profile" element={<div>Account</div>} />
          <Route path="/register" element={<div>Register</div>} />
        </Routes>
      </StudentTermsGate>
    </MemoryRouter>,
  )
}

describe('StudentTermsGate', () => {
  beforeEach(() => {
    hasSignedInMock.mockReset()
    fetchMeMock.mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  it('redirects signed-in students missing terms to account from protected routes', async () => {
    hasSignedInMock.mockResolvedValue(true)
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 's@example.com',
      role: 'student',
      termsAcceptedAt: '',
      privacyAcceptedAt: '',
    })

    renderAt('/courses')

    await waitFor(() => {
      expect(screen.getByText('Account')).toBeTruthy()
    })
  })

  it('allows navigation on public register route without redirect', async () => {
    hasSignedInMock.mockResolvedValue(true)
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 's@example.com',
      role: 'student',
      termsAcceptedAt: '',
      privacyAcceptedAt: '',
    })

    renderAt('/register')

    await waitFor(() => {
      expect(screen.getByText('Register')).toBeTruthy()
    })
    expect(screen.queryByText('Account')).toBeNull()
  })

  it('redirects to account when profile fetch fails for a signed-in student', async () => {
    hasSignedInMock.mockResolvedValue(true)
    fetchMeMock.mockRejectedValue(new Error('network'))

    renderAt('/courses')

    await waitFor(() => {
      expect(screen.getByText('Account')).toBeTruthy()
    })
  })

  it('allows courses when both acceptance timestamps are set', async () => {
    hasSignedInMock.mockResolvedValue(true)
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 's@example.com',
      role: 'student',
      termsAcceptedAt: '2026-01-01T00:00:00.000Z',
      privacyAcceptedAt: '2026-01-01T00:00:00.000Z',
    })

    renderAt('/courses')

    await waitFor(() => {
      expect(screen.getByText('Courses')).toBeTruthy()
    })
  })
})
