/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())
const useCognitoDisplayNameMock = vi.hoisted(() => vi.fn())

vi.mock('@aws-amplify/ui-react', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

vi.mock('../lib/cognito-display-name', () => ({
  useCognitoDisplayName: (...args: unknown[]) => useCognitoDisplayNameMock(...args),
}))

describe('TeacherHeader', () => {
  async function loadHeader() {
    return (await import('./TeacherHeader')).TeacherHeader
  }

  async function renderTestRoot() {
    const TeacherHeader = await loadHeader()
    return render(
      <AuthenticatorProvider>
        <MemoryRouter initialEntries={['/']}>
          <TeacherHeader />
        </MemoryRouter>
      </AuthenticatorProvider>,
    )
  }

  beforeEach(() => {
    useAuthenticatorMock.mockReset()
    useCognitoDisplayNameMock.mockReset()
    useCognitoDisplayNameMock.mockReturnValue({ label: 'Alex', title: 'Alex', ready: true })
    vi.unstubAllEnvs()
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
    vi.resetModules()
  })

  it('shows Instructor badge and Dashboard link on home', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: { username: 'teacher@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    expect(screen.getByText('Instructor')).toBeTruthy()
    const main = screen.getByRole('navigation', { name: 'Main' })
    expect(within(main).getByRole('link', { name: 'Dashboard' }).getAttribute('href')).toBe('/')
  })

  it('uses VITE_STUDENT_SITE_URL for student site link when set', async () => {
    vi.stubEnv('VITE_STUDENT_SITE_URL', 'https://student.example.test/')
    vi.resetModules()
    useAuthenticatorMock.mockReturnValue({
      user: { username: 't@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    const link = screen.getByRole('link', { name: /View Student Site/i })
    expect(link.getAttribute('href')).toBe('https://student.example.test/')
  })

  it('calls signOut from desktop control', async () => {
    const signOut = vi.fn().mockResolvedValue(undefined)
    useAuthenticatorMock.mockReturnValue({
      user: { username: 't@example.com' },
      signOut,
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1))
  })

  it('closes mobile menu on route change', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: undefined,
      signOut: vi.fn(),
      authStatus: 'unauthenticated',
    })
    const TeacherHeader = await loadHeader()
    function Shell() {
      return (
        <>
          <TeacherHeader />
          <Routes>
            <Route path="/" element={<div>Dashboard body</div>} />
            <Route path="/courses/:courseId" element={<div>Course stub</div>} />
          </Routes>
        </>
      )
    }
    render(
      <AuthenticatorProvider>
        <MemoryRouter initialEntries={['/courses/c1']}>
          <Shell />
        </MemoryRouter>
      </AuthenticatorProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    const mobileNav = screen.getByRole('navigation', { name: 'Mobile' })
    fireEvent.click(within(mobileNav).getByRole('link', { name: 'Dashboard' }))
    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: 'Mobile' })).toBeNull()
    })
  })

  it('applies scroll shadow when window is scrolled', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: { username: 't@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    const { container } = await renderTestRoot()
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
