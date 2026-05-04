/**
 * @vitest-environment jsdom
 */
import { afterEach } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Amplify } from 'aws-amplify'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { POST_LOGIN_RETURN_TO_KEY } from '../../lib/post-login-return'
import { GOOGLE_SIGN_IN_LABEL, SignIn } from './SignIn'

const { signInMock } = vi.hoisted(() => ({ signInMock: vi.fn() }))

vi.mock('aws-amplify/auth', () => ({
  signInWithRedirect: (...args: unknown[]) => signInMock(...args),
}))

function TestRoot({ children }: { children: React.ReactNode }) {
  return <AuthenticatorProvider>{children}</AuthenticatorProvider>
}

describe('SignIn', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    signInMock.mockClear()
    sessionStorage.clear()
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId: 'eu-west-1_testPool',
          userPoolClientId: 'testClientId',
          loginWith: {
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

  it('shows only Continue with Google and no username/password inputs', async () => {
    render(<SignIn />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))

    expect(button.tagName).toBe('BUTTON')
    expect(document.querySelector('input[type="password"]')).toBeNull()
    expect(document.querySelector('input[type="email"]')).toBeNull()
    expect(screen.queryByRole('textbox')).toBeNull()
    expect(screen.queryByLabelText(/password/i)).toBeNull()
  })

  it('calls signInWithRedirect with Google provider when Continue with Google is clicked', async () => {
    render(<SignIn />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))
    fireEvent.click(button)

    expect(signInMock).toHaveBeenCalledTimes(1)
    expect(signInMock).toHaveBeenCalledWith(expect.objectContaining({ provider: 'Google' }))
  })

  it('persists a safe returnTo path in sessionStorage before redirect', async () => {
    window.history.pushState({}, '', '/courses/abc?tab=lessons#l1')

    render(<SignIn />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))
    fireEvent.click(button)

    expect(sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)).toBe('/courses/abc?tab=lessons#l1')
    expect(signInMock).toHaveBeenCalledTimes(1)
  })

  it('does not persist returnTo when on /login', async () => {
    window.history.pushState({}, '', '/login')

    render(<SignIn />, { wrapper: TestRoot })

    const button = await waitFor(() => screen.getByRole('button', { name: GOOGLE_SIGN_IN_LABEL }))
    fireEvent.click(button)

    expect(sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)).toBeNull()
    expect(signInMock).toHaveBeenCalledTimes(1)
  })
})
