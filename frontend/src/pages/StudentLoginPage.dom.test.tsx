/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { GOOGLE_SIGN_IN_LABEL } from '../components/auth/SignIn'
import StudentLoginPage from './StudentLoginPage'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())

vi.mock('../lib/auth-ui', () => ({
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

  it('renders RS login hero grid with Create Account link to /register', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })

    render(<TestRoot />)

    const root = screen.getByTestId('student-page-login')
    expect(root.className).toContain('pg-login')
    expect(screen.getByTestId('login-hero-column')).toBeTruthy()
    expect(screen.getByTestId('login-auth-card')).toBeTruthy()
    expect(screen.getByRole('link', { name: /create account/i }).getAttribute('href')).toBe('/register')
  })

  it('toggles password visibility from the eye control', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })

    render(<TestRoot />)

    const input = await screen.findByLabelText(/^password$/i)
    expect(input.getAttribute('type')).toBe('password')

    fireEvent.click(screen.getByRole('button', { name: 'Show password' }))

    expect(input.getAttribute('type')).toBe('text')
    expect(screen.getByRole('button', { name: 'Hide password' }).getAttribute('aria-pressed')).toBe('true')

    fireEvent.click(screen.getByRole('button', { name: 'Hide password' }))

    expect(input.getAttribute('type')).toBe('password')
    expect(screen.getByRole('button', { name: 'Show password' }).getAttribute('aria-pressed')).toBe('false')
  })

  it('renders the Login.html FAQ heading', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })

    render(<TestRoot />)

    expect(await screen.findByRole('heading', { name: 'Common Sign-In Questions' })).toBeTruthy()
  })

  it('shows unavailable message when Cognito env is incomplete', async () => {
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'client')
    vi.stubEnv('VITE_COGNITO_DOMAIN', '')
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })

    render(<TestRoot />)

    expect(
      await screen.findByText(/Sign-in is not available/i),
    ).toBeTruthy()
  })
})
