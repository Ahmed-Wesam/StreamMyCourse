/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const resetPasswordMock = vi.hoisted(() => vi.fn())

vi.mock('aws-amplify/auth', () => ({
  resetPassword: (...args: unknown[]) => resetPasswordMock(...args),
}))

import ForgotPasswordPage from './ForgotPasswordPage'

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    resetPasswordMock.mockReset()
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'client')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'd.example.com')
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('renders the ForgotPassword.html hero heading', () => {
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Forgot Your Password?' })).toBeTruthy()
  })

  it('shows the same success UI when resetPassword rejects (user not found style)', async () => {
    resetPasswordMock.mockRejectedValue(new Error('User does not exist.'))
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    )
    fireEvent.change(screen.getByLabelText(/^email address$/i), { target: { value: 'missing@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /send reset instructions/i }))

    await waitFor(() => {
      expect(screen.getByRole('status').textContent).toMatch(/if an account exists/i)
    })
  })

  it('shows the same success UI when resetPassword succeeds', async () => {
    resetPasswordMock.mockResolvedValue({ nextStep: { resetPasswordStep: 'DONE' } })
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    )
    fireEvent.change(screen.getByLabelText(/^email address$/i), { target: { value: 'found@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /send reset instructions/i }))

    await waitFor(() => {
      expect(screen.getByRole('status').textContent).toMatch(/if an account exists/i)
    })
  })
})
