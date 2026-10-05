/**
 * @vitest-environment jsdom
 */
import { Amplify } from 'aws-amplify'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const signUpMock = vi.hoisted(() => vi.fn())
const useAuthenticatorMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  signUp: (...args: unknown[]) => signUpMock(...args),
}))

vi.mock('../lib/auth-ui', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

const navigateMock = vi.hoisted(() => vi.fn())
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

import StudentRegisterPage from './StudentRegisterPage'
import { REGISTER_PROFILE_DRAFT_KEY } from '../lib/register-profile-draft'

function renderPage() {
  return render(
    <AuthenticatorProvider>
      <MemoryRouter>
        <StudentRegisterPage />
      </MemoryRouter>
    </AuthenticatorProvider>,
  )
}

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Ada' } })
  fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'Lovelace' } })
  fireEvent.change(screen.getByLabelText(/^email address$/i), { target: { value: 'ada@example.com' } })
  fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Str0ngPass' } })
  fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'Str0ngPass' } })
  fireEvent.change(screen.getByLabelText(/^country$/i), { target: { value: 'Jordan' } })
  fireEvent.change(screen.getByLabelText(/^profession$/i), { target: { value: 'Researcher' } })
}

describe('StudentRegisterPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    signUpMock.mockReset()
    navigateMock.mockReset()
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'client')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'd.example.com')
    signUpMock.mockResolvedValue({ isSignUpComplete: false, nextStep: { signUpStep: 'CONFIRM_SIGN_UP' } })
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId: 'eu-west-1_test',
          userPoolClientId: 'client',
          loginWith: { email: true },
        },
      },
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('renders the Register.html journey heading', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: 'What Happens After You Register' })).toBeTruthy()
  })

  it('keeps submit disabled until required fields, matching passwords, and both checkboxes', async () => {
    renderPage()
    const submit = screen.getByTestId('register-submit') as HTMLButtonElement
    expect(submit.disabled).toBe(true)

    fillRequiredFields()
    expect(submit.disabled).toBe(true)

    fireEvent.click(screen.getByRole('checkbox', { name: /terms & conditions/i }))
    expect(submit.disabled).toBe(true)

    fireEvent.click(screen.getByRole('checkbox', { name: /privacy policy/i }))
    expect(submit.disabled).toBe(false)
  })

  it('password checklist does not require a symbol', () => {
    renderPage()
    const list = screen.getByTestId('password-checklist')
    expect(list.textContent?.toLowerCase()).not.toMatch(/symbol/)
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'Str0ngPass' } })
    expect(list.querySelectorAll('svg').length).toBeGreaterThan(0)
  })

  it('keeps Google sign-up disabled until both legal checkboxes are checked', () => {
    renderPage()
    const google = screen.getByTestId('register-google') as HTMLButtonElement
    expect(google.disabled).toBe(true)
    fireEvent.click(screen.getByRole('checkbox', { name: /terms & conditions/i }))
    expect(google.disabled).toBe(true)
    fireEvent.click(screen.getByRole('checkbox', { name: /privacy policy/i }))
    expect(google.disabled).toBe(false)
  })

  it('stores draft without password and calls signUp on submit', async () => {
    renderPage()
    fillRequiredFields()
    fireEvent.click(screen.getByRole('checkbox', { name: /terms & conditions/i }))
    fireEvent.click(screen.getByRole('checkbox', { name: /privacy policy/i }))
    fireEvent.click(screen.getByTestId('register-submit'))

    await waitFor(() => expect(signUpMock).toHaveBeenCalled())
    expect(signUpMock).toHaveBeenCalledWith(
      expect.objectContaining({
        username: 'ada@example.com',
        password: 'Str0ngPass',
      }),
    )
    const raw = sessionStorage.getItem(REGISTER_PROFILE_DRAFT_KEY)
    expect(raw?.toLowerCase()).not.toMatch(/password/)
    expect(JSON.parse(raw ?? '{}').email).toBe('ada@example.com')
    await waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith('/verify-email?email=ada%40example.com', { replace: true }),
    )
  })
})
