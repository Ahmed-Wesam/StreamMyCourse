/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMeMock = vi.hoisted(() => vi.fn())
const getPurchasesMock = vi.hoisted(() => vi.fn())
const listMyCertificatesMock = vi.hoisted(() => vi.fn())
const getMyResearchTeamMock = vi.hoisted(() => vi.fn())

vi.mock('../../lib/api/session', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api/session')>()
  return { ...actual, fetchMe: (...args: unknown[]) => fetchMeMock(...args) }
})

vi.mock('../../lib/api/billing', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api/billing')>()
  return { ...actual, getPurchases: (...args: unknown[]) => getPurchasesMock(...args) }
})

vi.mock('../../lib/api/certificates', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api/certificates')>()
  return { ...actual, listMyCertificates: (...args: unknown[]) => listMyCertificatesMock(...args) }
})

vi.mock('../../lib/api/research-team', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api/research-team')>()
  return { ...actual, getMyResearchTeam: (...args: unknown[]) => getMyResearchTeamMock(...args) }
})

import { AccountLayout } from './AccountLayout'

describe('AccountLayout', () => {
  beforeEach(() => {
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 'student@example.com',
      role: 'student',
      cognitoSub: 'sub',
      createdAt: '2026-01-01T00:00:00.000Z',
      updatedAt: '2026-01-01T00:00:00.000Z',
    })
    getPurchasesMock.mockResolvedValue([])
    listMyCertificatesMock.mockResolvedValue({ certificates: [] })
    getMyResearchTeamMock.mockResolvedValue({ courses: [], eligible: false, canSubmit: false, application: null })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders sidebar links for Profile and My purchases', () => {
    render(
      <MemoryRouter initialEntries={['/account/profile']}>
        <Routes>
          <Route path="/account" element={<AccountLayout />}>
            <Route path="profile" element={<div>Profile content</div>} />
            <Route path="purchases" element={<div>Purchases content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    const nav = screen.getByRole('navigation', { name: /account/i })
    expect(nav).toBeTruthy()

    const profile = screen.getByRole('link', { name: 'Profile' })
    expect(profile.getAttribute('href')).toBe('/account/profile')

    const purchases = screen.getByRole('link', { name: 'My purchases' })
    expect(purchases.getAttribute('href')).toBe('/account/purchases')
  })

  it('layout root uses pg-account prototype scope', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/account/profile']}>
        <Routes>
          <Route path="/account" element={<AccountLayout />}>
            <Route path="profile" element={<div>Profile content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(container.querySelector('.pg-account')).toBeTruthy()
  })
})
