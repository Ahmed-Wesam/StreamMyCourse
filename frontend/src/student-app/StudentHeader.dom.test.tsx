/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { StudentHeader } from './StudentHeader'

const api = vi.hoisted(() => ({
  hasSignedInIdToken: vi.fn(),
}))

const auth = vi.hoisted(() => ({
  isAuthConfigured: vi.fn(),
}))

const amplifyAuth = vi.hoisted(() => ({
  signOut: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    hasSignedInIdToken: (...args: unknown[]) =>
      api.hasSignedInIdToken(...args) as ReturnType<typeof mod.hasSignedInIdToken>,
  }
})

vi.mock('../lib/auth', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/auth')
  return {
    ...mod,
    isAuthConfigured: (...args: unknown[]) =>
      auth.isAuthConfigured(...args) as ReturnType<typeof mod.isAuthConfigured>,
  }
})

vi.mock('aws-amplify/auth', () => ({
  signOut: (...args: unknown[]) => amplifyAuth.signOut(...args),
}))

describe('StudentHeader', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders primary navigation links', () => {
    auth.isAuthConfigured.mockReturnValue(false)
    render(
      <MemoryRouter initialEntries={['/']}>
        <StudentHeader />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Home' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Course' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'My Course' })).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Pricing' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: 'Enroll Now' }).length).toBeGreaterThan(0)
  })

  it('shows Sign in when signed out and auth is configured', async () => {
    auth.isAuthConfigured.mockReturnValue(true)
    api.hasSignedInIdToken.mockResolvedValue(false)

    render(
      <MemoryRouter initialEntries={['/']}>
        <StudentHeader />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('link', { name: 'Sign in' })).toBeTruthy()
  })

  it('replaces Sign in with Sign out when signed in and clears storage/cookies on sign out', async () => {
    auth.isAuthConfigured.mockReturnValue(true)
    api.hasSignedInIdToken.mockResolvedValue(true)
    amplifyAuth.signOut.mockResolvedValue(undefined)

    localStorage.setItem('t', '1')
    document.cookie = 'a=b'

    render(
      <MemoryRouter initialEntries={['/']}>
        <StudentHeader />
      </MemoryRouter>,
    )

    const out = await screen.findByRole('button', { name: 'Sign out' })
    fireEvent.click(out)

    await waitFor(() => expect(amplifyAuth.signOut).toHaveBeenCalledTimes(1))
    expect(localStorage.getItem('t')).toBeNull()
    expect(document.cookie).not.toMatch(/a=b/)
  })

  it('closes mobile menu on route change', async () => {
    auth.isAuthConfigured.mockReturnValue(false)
    function Shell() {
      return (
        <>
          <StudentHeader />
          <Routes>
            <Route path="/" element={<div>Home body</div>} />
            <Route path="/course" element={<div>Course body</div>} />
          </Routes>
        </>
      )
    }

    render(
      <MemoryRouter initialEntries={['/']}>
        <Shell />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    const mobileNav = screen.getByRole('navigation', { name: /mobile/i })
    expect(mobileNav).toBeTruthy()

    fireEvent.click(within(mobileNav).getByRole('link', { name: 'Course' }))
    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: /mobile/i })).toBeNull()
    })
  })

  it('applies scroll shadow class when window is scrolled', async () => {
    auth.isAuthConfigured.mockReturnValue(false)
    const { container } = render(
      <MemoryRouter initialEntries={['/']}>
        <StudentHeader />
      </MemoryRouter>,
    )
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

