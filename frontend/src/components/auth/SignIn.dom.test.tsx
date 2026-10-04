/**
 * @vitest-environment jsdom
 */
import { afterEach } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Amplify } from 'aws-amplify'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { POST_LOGIN_RETURN_TO_KEY } from '../../lib/post-login-return'
import { GOOGLE_SIGN_IN_LABEL, SignIn } from './SignIn'

const authMocks = vi.hoisted(() => ({
  signInWithRedirect: vi.fn(),
  signIn: vi.fn(),
}))

vi.mock('aws-amplify/auth', () => ({
  signInWithRedirect: (...args: unknown[]) => authMocks.signInWithRedirect(...args),
  signIn: (...args: unknown[]) => authMocks.signIn(...args),
}))

function TestRoot({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter>
      <AuthenticatorProvider>{children}</AuthenticatorProvider>
    </MemoryRouter>
  )
}

describe('SignIn', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    authMocks.signInWithRedirect.mockClear()
    authMocks.signIn.mockClear()
    sessionStorage.clear()
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId: 'eu-west-1_testPool',
          userPoolClientId: 'testClientId',
          loginWith: {
            email: true,
            oauth: {
              domain: 'test.auth.eu-west-1.amazoncognito.com',
              scopes: ['openid', 'email', 'profile', 'aws.cognito.signin.user.admin'],
              redirectSignIn: ['http://localhost/'],
              redirectSignOut: ['http://localhost/'],
              responseType: 'code',
            },
          },
        },
      },
    })
  })

  it('student variant shows email, password, forgot link, and Google button', async () => {
    render(<SignIn variant="student" />, { wrapper: TestRoot })

    expect(await screen.findByLabelText(/^email$/i)).toBeTruthy()
    expect(screen.getByLabelText(/^password$/i)).toBeTruthy()
    expect(screen.getByRole('link', { name: /forgot password/i }).getAttribute('href')).toBe('/forgot-password')
    expect(screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL })).toBeTruthy()
    expect(screen.getByRole('link', { name: /create account/i }).getAttribute('href')).toBe('/register')
    expect(screen.getByTestId('signin-page-chrome')).toBeTruthy()
    expect(screen.getByTestId('login-auth-card').className).toMatch(/max-w-\[420px\]/)
  })

  it('embedded mode skips page chrome', async () => {
    render(<SignIn variant="student" embedded />, { wrapper: TestRoot })

    expect(await screen.findByLabelText(/^email$/i)).toBeTruthy()
    expect(screen.queryByTestId('signin-page-chrome')).toBeNull()
    expect(screen.getByTestId('login-auth-card').className).toMatch(/max-w-\[420px\]/)
  })

  it('teacher variant shows Google only (no email/password form)', async () => {
    render(<SignIn variant="teacher" />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))
    expect(button).toBeTruthy()
    expect(document.querySelector('input[type="password"]')).toBeNull()
    expect(document.querySelector('input[type="email"]')).toBeNull()
    expect(screen.queryByRole('link', { name: /forgot password/i })).toBeNull()
  })

  it('calls signInWithRedirect with Google provider when Continue with Google is clicked', async () => {
    render(<SignIn variant="student" />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))
    fireEvent.click(button)

    expect(authMocks.signInWithRedirect).toHaveBeenCalledTimes(1)
    expect(authMocks.signInWithRedirect).toHaveBeenCalledWith(expect.objectContaining({ provider: 'Google' }))
  })

  it('persists a safe returnTo path in sessionStorage before redirect', async () => {
    window.history.pushState({}, '', '/courses/abc?tab=lessons#l1')

    render(<SignIn variant="student" />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))
    fireEvent.click(button)

    expect(sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)).toBe('/courses/abc?tab=lessons#l1')
    expect(authMocks.signInWithRedirect).toHaveBeenCalledTimes(1)
  })

  it('does not persist returnTo when on /login', async () => {
    window.history.pushState({}, '', '/login')

    render(<SignIn variant="student" />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))
    fireEvent.click(button)

    expect(sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)).toBeNull()
    expect(authMocks.signInWithRedirect).toHaveBeenCalledTimes(1)
  })
})
