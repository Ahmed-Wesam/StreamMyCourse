/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const confirmSignUpMock = vi.hoisted(() => vi.fn())
const signInMock = vi.hoisted(() => vi.fn())
const fetchAuthSessionMock = vi.hoisted(() => vi.fn())
const patchUsersMeMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  confirmSignUp: (...args: unknown[]) => confirmSignUpMock(...args),
  signIn: (...args: unknown[]) => signInMock(...args),
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

vi.mock('../lib/auth-ui', () => ({
  useAuthenticator: () => ({ authStatus: 'unauthenticated' }),
}))

vi.mock('../lib/api/session', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api/session')>()
  return {
    ...actual,
    patchUsersMe: (...args: unknown[]) => patchUsersMeMock(...args),
  }
})

import VerifyEmailPage from './VerifyEmailPage'
import { REGISTER_PROFILE_DRAFT_KEY, saveRegisterProfileDraft } from '../lib/register-profile-draft'

function renderAt(email = 'ada@example.com') {
  return render(
    <AuthenticatorProvider>
      <MemoryRouter initialEntries={[`/verify-email?email=${encodeURIComponent(email)}`]}>
        <Routes>
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/account/profile" element={<div>Account profile</div>} />
        </Routes>
      </MemoryRouter>
    </AuthenticatorProvider>,
  )
}

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    confirmSignUpMock.mockResolvedValue({ isSignUpComplete: true, nextStep: { signUpStep: 'DONE' } })
    signInMock.mockResolvedValue({ isSignedIn: true })
    fetchAuthSessionMock.mockResolvedValue({ tokens: {} })
    patchUsersMeMock.mockResolvedValue({ userId: 'u1', email: 'ada@example.com' })
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'client')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'd.example.com')
    saveRegisterProfileDraft({
      email: 'ada@example.com',
      givenName: 'Ada',
      familyName: 'Lovelace',
      country: 'Jordan',
      profession: 'Researcher',
      institution: '',
      researchInterests: '',
      termsAccepted: true,
      privacyAccepted: true,
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('confirmSignUp, signIn, PATCH /users/me, clears draft without password in sessionStorage', async () => {
    renderAt()
    fireEvent.change(screen.getByLabelText(/verification code/i), { target: { value: '123456' } })
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Str0ngPass' } })
    fireEvent.click(screen.getByRole('button', { name: /verify and continue/i }))

    await waitFor(() => {
      expect(confirmSignUpMock).toHaveBeenCalledWith({
        username: 'ada@example.com',
        confirmationCode: '123456',
      })
    })
    expect(signInMock).toHaveBeenCalledWith({ username: 'ada@example.com', password: 'Str0ngPass' })
    expect(patchUsersMeMock).toHaveBeenCalled()
    expect(fetchAuthSessionMock).toHaveBeenCalledWith({ forceRefresh: true })
    expect(sessionStorage.getItem(REGISTER_PROFILE_DRAFT_KEY)).toBeNull()
    const keys = Object.keys(sessionStorage)
    for (const key of keys) {
      expect(sessionStorage.getItem(key)?.toLowerCase()).not.toMatch(/password/)
    }
    await waitFor(() => expect(screen.getByText('Account profile')).toBeTruthy())
  })
})
