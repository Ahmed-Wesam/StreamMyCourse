/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { fireEvent } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../lib/api'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())
const fetchMeMock = vi.hoisted(() => vi.fn())
const isAuthConfiguredMock = vi.hoisted(() => vi.fn())

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

vi.mock('../../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...actual,
    fetchMe: (...args: unknown[]) => fetchMeMock(...args),
  }
})

vi.mock('../../lib/auth', () => ({
  isAuthConfigured: () => isAuthConfiguredMock(),
}))

import { TeacherRoleGate } from './TeacherRoleGate'

function renderGate() {
  return render(
    <AuthenticatorProvider>
      <TeacherRoleGate>
        <div data-testid="teacher-shell-inner">allowed</div>
      </TeacherRoleGate>
    </AuthenticatorProvider>,
  )
}

describe('TeacherRoleGate', () => {
  beforeEach(() => {
    useAuthenticatorMock.mockReset()
    fetchMeMock.mockReset()
    isAuthConfiguredMock.mockReturnValue(true)
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows Cognito setup message when auth env is incomplete', () => {
    isAuthConfiguredMock.mockReturnValue(false)
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut: vi.fn() })
    renderGate()
    expect(screen.getByText(/Cognito is not configured for this build/i)).toBeTruthy()
  })

  it('renders nothing while signed out', () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated', signOut: vi.fn() })
    const { container } = renderGate()
    expect(container.textContent).not.toMatch(/allowed/)
  })

  it('shows loading then children for teacher role', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut: vi.fn() })
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 't@example.com',
      role: 'teacher',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
    })
    renderGate()
    expect(screen.getByText(/Loading profile/i)).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByTestId('teacher-shell-inner')).toBeTruthy()
    })
  })

  it('shows loading then children for admin role', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut: vi.fn() })
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 'a@example.com',
      role: 'ADMIN',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
    })
    renderGate()
    await waitFor(() => {
      expect(screen.getByTestId('teacher-shell-inner')).toBeTruthy()
    })
  })

  it('shows instructor access message when profile role is not teacher or admin', async () => {
    const signOut = vi.fn()
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut })
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 's@example.com',
      role: 'student',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
    })
    renderGate()
    await waitFor(() => {
      expect(screen.getByText(/Instructor access required/i)).toBeTruthy()
    })
    const btn = screen.getByRole('button', { name: /sign out/i })
    fireEvent.click(btn)
    expect(signOut).toHaveBeenCalledTimes(1)
  })

  it('shows error when /users/me fails', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut: vi.fn() })
    fetchMeMock.mockRejectedValue(new Error('network down'))
    renderGate()
    await waitFor(() => {
      expect(screen.getByText('network down')).toBeTruthy()
    })
  })

  it('shows instructor access message (not raw Unauthorized) when /users/me returns 401', async () => {
    const signOut = vi.fn()
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut })
    fetchMeMock.mockRejectedValue(new ApiError('Unauthorized', 401))
    renderGate()
    await waitFor(() => {
      expect(screen.getByText(/Sign-in required/i)).toBeTruthy()
    })
    expect(screen.queryByText(/^Unauthorized$/i)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(signOut).toHaveBeenCalledTimes(1)
  })

  it('shows instructor access message when /users/me returns 403', async () => {
    const signOut = vi.fn()
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut })
    fetchMeMock.mockRejectedValue(new ApiError('Forbidden', 403))
    renderGate()
    await waitFor(() => {
      expect(screen.getByText(/Instructor access required/i)).toBeTruthy()
    })
    expect(screen.queryByText(/^Forbidden$/i)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(signOut).toHaveBeenCalledTimes(1)
  })

  it('stays on loading when fetchMe never resolves', () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated', signOut: vi.fn() })
    fetchMeMock.mockReturnValue(new Promise(() => {}))
    renderGate()
    expect(screen.getByText(/Loading profile/i)).toBeTruthy()
    expect(screen.queryByTestId('teacher-shell-inner')).toBeNull()
  })
})
