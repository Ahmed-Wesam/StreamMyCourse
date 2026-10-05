/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { AuthenticatorProvider } from '@aws-amplify/ui-react-core'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const useAuthenticatorMock = vi.hoisted(() => vi.fn())
const useCognitoDisplayNameMock = vi.hoisted(() => vi.fn())
const fetchMeMock = vi.hoisted(() => vi.fn())

vi.mock('../lib/auth-ui', () => ({
  useAuthenticator: (...args: unknown[]) => useAuthenticatorMock(...args),
}))

vi.mock('../lib/cognito-display-name', () => ({
  useCognitoDisplayName: (...args: unknown[]) => useCognitoDisplayNameMock(...args),
}))

vi.mock('../lib/api/session', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api/session')
  return {
    ...mod,
    fetchMe: (...args: unknown[]) => fetchMeMock(...args) as ReturnType<typeof mod.fetchMe>,
  }
})

async function openProfileMenu() {
  const trigger = await screen.findByRole('button', { name: /Account menu/i })
  fireEvent.click(trigger)
  return screen.getByRole('menu')
}

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
    fetchMeMock.mockReset()
    useCognitoDisplayNameMock.mockReturnValue({ label: 'Alex', title: 'Alex', ready: true })
    fetchMeMock.mockResolvedValue({
      userId: 'u1',
      email: 'teacher@example.com',
      role: 'teacher',
      cognitoSub: 'sub-t',
      createdAt: '',
      updatedAt: '',
    })
    vi.unstubAllEnvs()
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
    vi.resetModules()
  })

  it('shows Instructor badge and Dashboard and Pricing links on home', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: { username: 'teacher@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    expect(screen.getAllByText('Instructor').length).toBeGreaterThanOrEqual(1)
    const main = screen.getByRole('navigation', { name: 'Primary' })
    expect(within(main).getByRole('link', { name: 'Dashboard' }).getAttribute('href')).toBe('/')
    expect(within(main).getByRole('link', { name: 'Pricing' }).getAttribute('href')).toBe(
      '/settings/payments',
    )
  })

  it('shows Research Team nav link when role is admin', async () => {
    fetchMeMock.mockResolvedValue({
      userId: 'u-admin',
      email: 'admin@example.com',
      role: 'admin',
      cognitoSub: 'sub-a',
      createdAt: '',
      updatedAt: '',
    })
    useAuthenticatorMock.mockReturnValue({
      user: { username: 'admin@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    const main = screen.getByRole('navigation', { name: 'Primary' })
    await waitFor(() => {
      expect(within(main).getByRole('link', { name: 'Research Team' }).getAttribute('href')).toBe(
        '/research-team/applications',
      )
    })
  })

  it('does not show Research Team nav link when role is teacher', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: { username: 'teacher@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    const main = screen.getByRole('navigation', { name: 'Primary' })
    await waitFor(() => {
      expect(fetchMeMock).toHaveBeenCalled()
    })
    expect(within(main).queryByRole('link', { name: 'Research Team' })).toBeNull()
  })

  it('uses sticky positioning so page content is not hidden under the header', async () => {
    useAuthenticatorMock.mockReturnValue({
      user: { username: 'teacher@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    const { container } = await renderTestRoot()
    const header = container.querySelector('header')
    expect(header?.className).toContain('rs-site-header')
    expect(header?.className).not.toMatch(/fixed/)
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
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toMatch(/noopener/)
  })

  it('uses researchspectrum.org fallback for student site link when VITE_STUDENT_SITE_URL is unset', async () => {
    vi.resetModules()
    useAuthenticatorMock.mockReturnValue({
      user: { username: 't@example.com' },
      signOut: vi.fn(),
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    const link = screen.getByRole('link', { name: /View Student Site/i })
    expect(link.getAttribute('href')).toBe('https://researchspectrum.org')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toMatch(/noopener/)
  })

  it('calls signOut from desktop ProfileMenu', async () => {
    const signOut = vi.fn().mockResolvedValue(undefined)
    useAuthenticatorMock.mockReturnValue({
      user: { username: 't@example.com' },
      signOut,
      authStatus: 'authenticated',
    })
    await renderTestRoot()
    const menu = await openProfileMenu()
    fireEvent.click(within(menu).getByRole('menuitem', { name: 'Sign out' }))
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
    const mobileNav = screen.getByRole('navigation', { name: /mobile/i })
    fireEvent.click(within(mobileNav).getByRole('link', { name: 'Dashboard' }))
    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: /mobile/i })).toBeNull()
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
    expect(header?.className).toContain('rs-site-header')
    expect(header?.className).not.toContain('rs-site-header-scrolled')
    const scrollSpy = vi.spyOn(window, 'scrollY', 'get').mockReturnValue(21)
    fireEvent.scroll(window)
    await waitFor(() => {
      expect(header?.className).toContain('rs-site-header-scrolled')
    })
    scrollSpy.mockRestore()
  })
})
