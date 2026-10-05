/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMeMock = vi.hoisted(() => vi.fn())
const patchUsersMeMock = vi.hoisted(() => vi.fn())
const fetchAuthSessionMock = vi.hoisted(() => vi.fn())
const updateUserAttributesMock = vi.hoisted(() => vi.fn())
const updatePasswordMock = vi.hoisted(() => vi.fn())

vi.mock('../../lib/api/session', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api/session')>()
  return {
    ...actual,
    fetchMe: (...args: unknown[]) => fetchMeMock(...args),
    patchUsersMe: (...args: unknown[]) => patchUsersMeMock(...args),
  }
})

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
  updateUserAttributes: (...args: unknown[]) => updateUserAttributesMock(...args),
  updatePassword: (...args: unknown[]) => updatePasswordMock(...args),
}))

const getPurchasesMock = vi.hoisted(() => vi.fn())
const listMyCertificatesMock = vi.hoisted(() => vi.fn())
const getMyResearchTeamMock = vi.hoisted(() => vi.fn())

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
import AccountProfilePage from './AccountProfilePage'

const baseProfile = {
  userId: 'user-1',
  email: 'student@example.com',
  role: 'student',
  cognitoSub: 'sub-1',
  createdAt: '2026-01-01T00:00:00.000Z',
  updatedAt: '2026-01-01T00:00:00.000Z',
  givenName: 'Ada',
  familyName: 'Lovelace',
  country: 'Jordan',
  profession: 'Researcher',
  termsAcceptedAt: '2026-01-01T00:00:00.000Z',
  privacyAcceptedAt: '2026-01-01T00:00:00.000Z',
}

describe('AccountProfilePage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  beforeEach(() => {
    fetchMeMock.mockReset()
    patchUsersMeMock.mockReset()
    fetchAuthSessionMock.mockReset()
    updateUserAttributesMock.mockReset()
    updatePasswordMock.mockReset()
    getPurchasesMock.mockReset()
    listMyCertificatesMock.mockReset()
    getMyResearchTeamMock.mockReset()
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: { payload: {} } } })
    patchUsersMeMock.mockImplementation(async (body) => ({ ...baseProfile, ...body }))
    updateUserAttributesMock.mockResolvedValue({})
    getPurchasesMock.mockResolvedValue([])
    listMyCertificatesMock.mockResolvedValue({ certificates: [] })
    getMyResearchTeamMock.mockResolvedValue({ courses: [], eligible: false, canSubmit: false, application: null })
  })

  function renderProfileRoute() {
    return render(
      <MemoryRouter initialEntries={['/account/profile']}>
        <Routes>
          <Route path="/account" element={<AccountLayout />}>
            <Route path="profile" element={<AccountProfilePage />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
  }

  it('shows prototype account hero heading Welcome back', async () => {
    fetchMeMock.mockResolvedValue(baseProfile)

    renderProfileRoute()

    expect(await screen.findByRole('heading', { level: 1, name: /welcome back/i })).toBeTruthy()
  })

  it('shows read-only email and saves via updateUserAttributes, forceRefresh, and PATCH', async () => {
    fetchMeMock.mockResolvedValue(baseProfile)

    render(
      <MemoryRouter>
        <AccountProfilePage />
      </MemoryRouter>,
    )

    const emailInput = await screen.findByLabelText(/email address/i)
    expect((emailInput as HTMLInputElement).readOnly).toBe(true)

    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Grace' } })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(updateUserAttributesMock).toHaveBeenCalledWith({
        userAttributes: { given_name: 'Grace', family_name: 'Lovelace' },
      })
    })
    expect(patchUsersMeMock).toHaveBeenCalled()
    expect(fetchAuthSessionMock).toHaveBeenCalledWith({ forceRefresh: true })
  })

  it('shows change-password section for native password users only', async () => {
    fetchMeMock.mockResolvedValue(baseProfile)
    fetchAuthSessionMock.mockResolvedValue({ tokens: { idToken: { payload: {} } } })

    render(
      <MemoryRouter>
        <AccountProfilePage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /change password/i })).toBeTruthy()
    })
  })

  it('hides change-password form for Google federated users', async () => {
    fetchMeMock.mockResolvedValue(baseProfile)
    fetchAuthSessionMock.mockResolvedValue({
      tokens: {
        idToken: {
          payload: {
            identities: JSON.stringify([{ providerName: 'Google', userId: 'g-1' }]),
          },
        },
      },
    })

    render(
      <MemoryRouter>
        <AccountProfilePage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/signed in with google/i)).toBeTruthy()
    })
    expect(screen.queryByRole('heading', { name: /change password/i })).toBeNull()
  })

  it('shows Research Team completion banner when complete=research-team', async () => {
    fetchMeMock.mockResolvedValue({
      ...baseProfile,
      country: '',
      profession: '',
    })

    render(
      <MemoryRouter initialEntries={['/account/profile?complete=research-team']}>
        <AccountProfilePage />
      </MemoryRouter>,
    )

    expect(await screen.findByTestId('profile-research-team-banner')).toBeTruthy()
    expect(screen.getByText(/country and profession/i)).toBeTruthy()
  })
})
