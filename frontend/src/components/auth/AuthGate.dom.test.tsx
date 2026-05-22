/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const AuthShellMock = vi.hoisted(() =>
  vi.fn(() => <div data-testid="auth-shell">AuthShell</div>),
)

vi.mock('./AuthShell', () => ({
  default: AuthShellMock,
}))

vi.mock('../../lib/auth-bootstrap', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/auth-bootstrap')>()
  return { ...actual }
})

import { AuthGate } from './AuthGate'

function TestRoot({ initialEntries }: { initialEntries: string[] }) {
  return (
    <AuthenticatorProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route
            path="*"
            element={
              <AuthGate>
                <div data-testid="gate-child">Child</div>
              </AuthGate>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthenticatorProvider>
  )
}

describe('AuthGate', () => {
  afterEach(() => {
    cleanup()
    AuthShellMock.mockClear()
    vi.restoreAllMocks()
  })

  it('renders children at / without loading AuthShell', () => {
    render(<TestRoot initialEntries={['/']} />)

    expect(screen.getByTestId('gate-child')).toBeTruthy()
    expect(AuthShellMock).not.toHaveBeenCalled()
  })

  it('loads AuthShell at OAuth callback with Suspense fallback', async () => {
    render(<TestRoot initialEntries={['/?code=x&state=y']} />)

    expect(screen.getByText('Loading…')).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByTestId('auth-shell')).toBeTruthy()
    })
    expect(AuthShellMock).toHaveBeenCalled()
  })

  it('loads AuthShell at /login', async () => {
    render(<TestRoot initialEntries={['/login']} />)

    await waitFor(() => {
      expect(screen.getByTestId('auth-shell')).toBeTruthy()
    })
    expect(AuthShellMock).toHaveBeenCalled()
  })
})
