/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { GOOGLE_SIGN_IN_LABEL } from '../components/auth/SignIn'
import StudentLoginPage from './StudentLoginPage'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

function TestRoot() {
  return (
    <AuthenticatorProvider>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="/login" element={<StudentLoginPage />} />
        </Routes>
      </MemoryRouter>
    </AuthenticatorProvider>
  )
}

describe('StudentLoginPage', () => {
  beforeEach(() => {
    useAuthenticatorMock.mockReset()
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'eu-west-1_testpool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'testclient')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'test.auth.eu-west-1.amazoncognito.com')
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
  })

  it('redirects to home when already authenticated', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })

    render(<TestRoot />)

    await waitFor(() => expect(screen.getByText('Home')).toBeTruthy())
  })

  it('shows Google sign-in when unauthenticated', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })

    render(<TestRoot />)

    expect(await screen.findByRole('button', { name: GOOGLE_SIGN_IN_LABEL })).toBeTruthy()
  })
})
