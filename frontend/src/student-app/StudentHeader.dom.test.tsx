/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { StudentHeader } from './StudentHeader'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())
const fetchAuthSessionMock = vi.hoisted(() => vi.fn())

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args: unknown[]) => fetchAuthSessionMock(...args),
}))

function TestRoot() {
  return (
    <AuthenticatorProvider>
      <MemoryRouter initialEntries={['/']}>
        <StudentHeader />
      </MemoryRouter>
    </AuthenticatorProvider>
  )
}

describe('StudentHeader', () => {
  beforeEach(() => {
    useAuthenticatorMock.mockReset()
    fetchAuthSessionMock.mockReset()
    fetchAuthSessionMock.mockResolvedValue({
      tokens: { idToken: { payload: { email: 'student@example.com' } } },
    })
    vi.stubEnv('VITE_COGNITO_USER_POOL_ID', 'eu-west-1_testpool')
    vi.stubEnv('VITE_COGNITO_USER_POOL_CLIENT_ID', 'testclient')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'test.auth.eu-west-1.amazoncognito.com')
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
  })

  it('shows Sign out when authenticated', async () => {
    const signOut = vi.fn().mockResolvedValue(undefined)
    useAuthenticatorMock.mockReturnValue({
      user: { username: 'student@example.com' },
      signOut,
      authStatus: 'authenticated',
    })

    render(<TestRoot />)

    expect(await screen.findByText('student')).toBeTruthy()
    const out = screen.getByRole('button', { name: 'Sign out' })
    fireEvent.click(out)
    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1))
  })

  it('shows Sign in when unauthenticated', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: undefined,
      signOut: vi.fn(),
      authStatus: 'unauthenticated',
    })

    render(<TestRoot />)

    expect(screen.getByRole('link', { name: 'Sign in' })).toBeTruthy()
  })

  it('closes mobile menu on route change', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: undefined,
      signOut: vi.fn(),
      authStatus: 'unauthenticated',
    })

    function Shell() {
      return (
        <>
          <StudentHeader />
          <Routes>
            <Route path="/" element={<div>Home body</div>} />
            <Route path="/login" element={<div>Login stub</div>} />
            <Route path="/other" element={<div>Other page</div>} />
          </Routes>
        </>
      )
    }

    render(
      <AuthenticatorProvider>
        <MemoryRouter initialEntries={['/']}>
          <Shell />
        </MemoryRouter>
      </AuthenticatorProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    const mobileNav = screen.getByRole('navigation', { name: 'Mobile' })
    expect(mobileNav).toBeTruthy()

    fireEvent.click(within(mobileNav).getByRole('link', { name: 'Sign in' }))
    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: 'Mobile' })).toBeNull()
    })
  })

  it('applies scroll shadow class when window is scrolled', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: undefined,
      signOut: vi.fn(),
      authStatus: 'unauthenticated',
    })

    const { container } = render(<TestRoot />)
    const header = container.querySelector('header')
    expect(header).toBeTruthy()
    expect(header?.className).not.toMatch(/shadow-sm/)

    const scrollSpy = vi.spyOn(window, 'scrollY', 'get').mockReturnValue(10)
    fireEvent.scroll(window)

    await waitFor(() => {
      expect(header?.className).toMatch(/shadow-sm/)
    })
    scrollSpy.mockRestore()
  })
})
