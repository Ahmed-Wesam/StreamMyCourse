/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())
const fetchMeMock = vi.hoisted(() => vi.fn())
const isAuthConfiguredMock = vi.hoisted(() => vi.fn())

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

vi.mock('../../lib/api', () => ({
  fetchMe: (...args: unknown[]) => fetchMeMock(...args),
}))

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
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })
    renderGate()
    expect(screen.getByText(/Cognito is not configured for this build/i)).toBeTruthy()
  })

  it('renders nothing while signed out', () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'unauthenticated' })
    const { container } = renderGate()
    expect(container.textContent).not.toMatch(/allowed/)
  })

  it('shows loading then children for teacher role', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })
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
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })
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
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })
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
  })

  it('shows error when /users/me fails', async () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })
    fetchMeMock.mockRejectedValue(new Error('network down'))
    renderGate()
    await waitFor(() => {
      expect(screen.getByText('network down')).toBeTruthy()
    })
  })

  it('stays on loading when fetchMe never resolves', () => {
    useAuthenticatorMock.mockReturnValue({ authStatus: 'authenticated' })
    fetchMeMock.mockReturnValue(new Promise(() => {}))
    renderGate()
    expect(screen.getByText(/Loading profile/i)).toBeTruthy()
    expect(screen.queryByTestId('teacher-shell-inner')).toBeNull()
  })
})
