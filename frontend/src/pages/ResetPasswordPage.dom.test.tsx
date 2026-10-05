/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ResetPasswordPage from './ResetPasswordPage'

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'pool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'client')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'd.example.com')
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('renders the ResetPassword.html hero heading', () => {
    render(
      <MemoryRouter>
        <ResetPasswordPage />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Create A New Password' })).toBeTruthy()
  })
})
