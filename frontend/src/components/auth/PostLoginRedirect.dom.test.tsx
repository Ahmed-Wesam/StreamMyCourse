/**
 * @vitest-environment jsdom
 */
import { cleanup, render, waitFor } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { Route, Routes } from 'react-router-dom'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { POST_LOGIN_RETURN_TO_KEY } from '../../lib/post-login-return'
import { PostLoginRedirect } from './PostLoginRedirect'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

function TestRoot({ initialEntries }: { initialEntries: string[] }) {
  return (
    <AuthenticatorProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <PostLoginRedirect />
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="/courses/:courseId" element={<div>Course</div>} />
          <Route path="/login" element={<div>Login</div>} />
        </Routes>
      </MemoryRouter>
    </AuthenticatorProvider>
  )
}

describe('PostLoginRedirect', () => {
  beforeEach(() => {
    sessionStorage.clear()
    useAuthenticatorMock.mockReset()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('navigates to stored returnTo and clears it when authenticated', async () => {
    sessionStorage.setItem(POST_LOGIN_RETURN_TO_KEY, '/courses/abc?tab=lessons#l1')
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })

    render(<TestRoot initialEntries={['/']} />)

    await waitFor(() => expect(document.body.textContent).toContain('Course'))
    expect(sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)).toBeNull()
  })

  it('ignores unsafe stored returnTo and clears it', async () => {
    sessionStorage.setItem(POST_LOGIN_RETURN_TO_KEY, '//evil.example.com')
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })

    render(<TestRoot initialEntries={['/']} />)

    await waitFor(() => expect(document.body.textContent).toContain('Home'))
    expect(sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)).toBeNull()
  })

  it('does nothing when not authenticated', async () => {
    sessionStorage.setItem(POST_LOGIN_RETURN_TO_KEY, '/courses/abc')
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })

    render(<TestRoot initialEntries={['/']} />)

    await waitFor(() => expect(document.body.textContent).toContain('Home'))
    expect(sessionStorage.getItem(POST_LOGIN_RETURN_TO_KEY)).toBe('/courses/abc')
  })
})

