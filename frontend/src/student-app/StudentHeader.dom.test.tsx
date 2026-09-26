/**
 * @vitest-environment jsdom
 */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SESSION_SUPERSEDED_BANNER_KEY } from '../lib/session-superseded-banner'
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

const sessionLazy = vi.hoisted(() => ({
  probeSignedIn: vi.fn(),
  warmUserProfileOnce: vi.fn(),
  getProfileDisplayNameOnce: vi.fn(),
  lazySignOut: vi.fn(),
}))

const hubListenMock = vi.hoisted(() => vi.fn().mockReturnValue(() => {}))

const idleCallbacks = vi.hoisted(() => [] as IdleRequestCallback[])

vi.mock('../lib/api/session', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api/session')
  return {
    ...mod,
    hasSignedInIdToken: (...args: unknown[]) =>
      api.hasSignedInIdToken(...args) as ReturnType<typeof mod.hasSignedInIdToken>,
  }
})

vi.mock('../lib/is-auth-configured', () => ({
  isAuthConfigured: (...args: unknown[]) =>
    auth.isAuthConfigured(...args) as boolean,
}))

vi.mock('../lib/auth-session-lazy', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/auth-session-lazy')
  return {
    ...mod,
    probeSignedIn: (...args: unknown[]) => sessionLazy.probeSignedIn(...args),
    warmUserProfileOnce: (...args: unknown[]) => sessionLazy.warmUserProfileOnce(...args),
    getProfileDisplayNameOnce: (...args: unknown[]) => sessionLazy.getProfileDisplayNameOnce(...args),
    lazySignOut: (...args: unknown[]) => sessionLazy.lazySignOut(...args),
  }
})

vi.mock('aws-amplify/auth', () => ({
  signOut: (...args: unknown[]) => amplifyAuth.signOut(...args),
}))

vi.mock('aws-amplify/utils', () => ({
  Hub: { listen: hubListenMock },
}))

const EXPECTED_NAV = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/courses', label: 'Courses' },
  { href: '/certificates', label: 'Certificates' },
  { href: '/research-team', label: 'Research Team' },
  { href: '/about', label: 'About Instructor' },
  { href: '/faq', label: 'FAQ' },
  { href: '/contact', label: 'Contact' },
] as const

function flushRequestIdleCallbacks() {
  const pending = [...idleCallbacks]
  idleCallbacks.length = 0
  for (const cb of pending) {
    cb({ didTimeout: false, timeRemaining: () => 50 } as IdleDeadline)
  }
}

async function openProfileMenu() {
  const trigger = await screen.findByRole('button', { name: /Account menu/i })
  fireEvent.click(trigger)
  return screen.getByRole('menu')
}

describe('StudentHeader', () => {
  beforeEach(() => {
    idleCallbacks.length = 0
    vi.stubGlobal('requestIdleCallback', (cb: IdleRequestCallback) => {
      idleCallbacks.push(cb)
      return 1
    })
    vi.stubGlobal('cancelIdleCallback', () => {})

    auth.isAuthConfigured.mockReturnValue(false)
    api.hasSignedInIdToken.mockReset()
    sessionLazy.probeSignedIn.mockReset()
    sessionLazy.warmUserProfileOnce.mockReset()
    sessionLazy.warmUserProfileOnce.mockResolvedValue(undefined)
    sessionLazy.getProfileDisplayNameOnce.mockReset()
    sessionLazy.getProfileDisplayNameOnce.mockResolvedValue(null)
    sessionLazy.lazySignOut.mockReset()
    sessionLazy.lazySignOut.mockResolvedValue(undefined)
    amplifyAuth.signOut.mockReset()
    hubListenMock.mockClear()
    hubListenMock.mockReturnValue(() => {})
  })

  afterEach(() => {
    cleanup()
    sessionStorage.clear()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders primary navigation links in prototype order', () => {
    auth.isAuthConfigured.mockReturnValue(false)
    render(
      <MemoryRouter initialEntries={['/']}>
        <StudentHeader />
      </MemoryRouter>,
    )

    const desktop = screen.getByRole('navigation', { name: 'Primary' })
    const desktopLinks = within(desktop).getAllByRole('link')
    expect(desktopLinks.map((el) => el.textContent)).toEqual(EXPECTED_NAV.map((l) => l.label))
    expect(desktopLinks.map((el) => el.getAttribute('href'))).toEqual(EXPECTED_NAV.map((l) => l.href))

    expect(screen.queryByRole('link', { name: 'Home' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Details' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Pricing' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Enroll Now' })).toBeNull()
  })

  it('shows Sign In and Create Account when signed out and auth is configured', async () => {
    auth.isAuthConfigured.mockReturnValue(true)
    api.hasSignedInIdToken.mockResolvedValue(false)
    sessionLazy.probeSignedIn.mockResolvedValue(false)

    render(
      <MemoryRouter initialEntries={['/']}>
        <StudentHeader />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('link', { name: 'Sign In' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Create Account' })).toBeTruthy()
    expect(screen.queryByRole('link', { name: 'Enroll Now' })).toBeNull()
  })

  it('keeps a newer display name when an older lookup resolves later', async () => {
    auth.isAuthConfigured.mockReturnValue(true)
    sessionLazy.probeSignedIn.mockResolvedValue(true)

    let resolveFirst: (value: string | null) => void = () => {}
    let markStarted: () => void = () => {}
    const firstStarted = new Promise<void>((resolve) => {
      markStarted = resolve
    })
    sessionLazy.getProfileDisplayNameOnce.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve
          markStarted()
        }),
    )
    sessionLazy.getProfileDisplayNameOnce.mockResolvedValue('Bob')

    function GoAccount() {
      const navigate = useNavigate()
      return (
        <button type="button" onClick={() => navigate('/account/profile')}>
          go account
        </button>
      )
    }

    render(
      <MemoryRouter initialEntries={['/login']}>
        <StudentHeader />
        <GoAccount />
      </MemoryRouter>,
    )

    await firstStarted
    fireEvent.click(screen.getByRole('button', { name: 'go account' }))

    expect(await screen.findByRole('button', { name: /Account menu for Bob/i })).toBeTruthy()
    resolveFirst(null)
    await act(async () => {})
    expect(screen.getByRole('button', { name: /Account menu for Bob/i })).toBeTruthy()
  })

  it('shows ProfileMenu Account and Logout when signed in; Logout calls lazySignOut and navigates home', async () => {
    auth.isAuthConfigured.mockReturnValue(true)
    sessionLazy.probeSignedIn.mockResolvedValue(true)
    sessionLazy.getProfileDisplayNameOnce.mockResolvedValue(null)

    localStorage.setItem('t', '1')
    document.cookie = 'a=b'

    function LocationProbe() {
      const location = useLocation()
      return <span data-testid="location-probe">{location.pathname}</span>
    }

    render(
      <MemoryRouter initialEntries={['/courses']}>
        <StudentHeader />
        <LocationProbe />
      </MemoryRouter>,
    )

    await act(async () => {
      flushRequestIdleCallbacks()
    })

    const menu = await openProfileMenu()
    expect(within(menu).getByRole('menuitem', { name: 'Account' })).toBeTruthy()
    const logout = within(menu).getByRole('menuitem', { name: 'Logout' })
    fireEvent.click(logout)

    await waitFor(() => expect(sessionLazy.lazySignOut).toHaveBeenCalledTimes(1))
    expect(localStorage.getItem('t')).toBeNull()
    expect(document.cookie).not.toMatch(/a=b/)
    await waitFor(() => {
      expect(screen.getByTestId('location-probe').textContent).toBe('/')
    })
  })

  it('closes mobile menu on route change', async () => {
    auth.isAuthConfigured.mockReturnValue(false)
    function Shell() {
      return (
        <>
          <StudentHeader />
          <Routes>
            <Route path="/" element={<div>Home body</div>} />
            <Route path="/courses" element={<div>Courses body</div>} />
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

    fireEvent.click(within(mobileNav).getByRole('link', { name: 'Courses' }))
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
    expect(header?.className).toContain('rs-site-header')
    expect(header?.className).not.toContain('rs-site-header-scrolled')

    const scrollSpy = vi.spyOn(window, 'scrollY', 'get').mockReturnValue(21)
    fireEvent.scroll(window)

    await waitFor(() => {
      expect(header?.className).toContain('rs-site-header-scrolled')
    })
    scrollSpy.mockRestore()
  })

  describe('lazy session probe (phase-1e)', () => {
    it('does not call probeSignedIn synchronously on public /; probes after requestIdleCallback', async () => {
      auth.isAuthConfigured.mockReturnValue(true)
      sessionLazy.probeSignedIn.mockResolvedValue(false)
      api.hasSignedInIdToken.mockResolvedValue(false)

      render(
        <MemoryRouter initialEntries={['/']}>
          <StudentHeader />
        </MemoryRouter>,
      )

      expect(sessionLazy.probeSignedIn).not.toHaveBeenCalled()
      expect(api.hasSignedInIdToken).not.toHaveBeenCalled()

      await act(async () => {
        flushRequestIdleCallbacks()
      })

      await waitFor(() => expect(sessionLazy.probeSignedIn).toHaveBeenCalledTimes(1))
      expect(api.hasSignedInIdToken).not.toHaveBeenCalled()
    })

    it('does not probe session while session-superseded banner is persisted', async () => {
      auth.isAuthConfigured.mockReturnValue(true)
      sessionStorage.setItem(SESSION_SUPERSEDED_BANNER_KEY, 'Signed in elsewhere')
      sessionLazy.probeSignedIn.mockResolvedValue(true)

      render(
        <MemoryRouter initialEntries={['/']}>
          <StudentHeader />
        </MemoryRouter>,
      )

      await act(async () => {
        flushRequestIdleCallbacks()
      })

      expect(sessionLazy.probeSignedIn).not.toHaveBeenCalled()
    })

    it('does not probe session on OAuth callback URL before auth shell (sync render)', async () => {
      auth.isAuthConfigured.mockReturnValue(true)
      sessionLazy.probeSignedIn.mockResolvedValue(false)
      api.hasSignedInIdToken.mockResolvedValue(false)

      render(
        <MemoryRouter initialEntries={['/?code=x&state=y']}>
          <StudentHeader />
        </MemoryRouter>,
      )

      expect(sessionLazy.probeSignedIn).not.toHaveBeenCalled()
      expect(api.hasSignedInIdToken).not.toHaveBeenCalled()

      await act(async () => {
        flushRequestIdleCallbacks()
      })

      expect(sessionLazy.probeSignedIn).not.toHaveBeenCalled()
      expect(api.hasSignedInIdToken).not.toHaveBeenCalled()
    })

    it('shows ProfileMenu Logout when probeSignedIn resolves true (idle probe)', async () => {
      auth.isAuthConfigured.mockReturnValue(true)
      sessionLazy.probeSignedIn.mockResolvedValue(true)
      api.hasSignedInIdToken.mockResolvedValue(false)

      render(
        <MemoryRouter initialEntries={['/']}>
          <StudentHeader />
        </MemoryRouter>,
      )

      await act(async () => {
        flushRequestIdleCallbacks()
      })

      const menu = await openProfileMenu()
      expect(within(menu).getByRole('menuitem', { name: 'Logout' })).toBeTruthy()
      expect(api.hasSignedInIdToken).not.toHaveBeenCalled()
      await waitFor(() => expect(sessionLazy.warmUserProfileOnce).toHaveBeenCalledWith(true))
      await waitFor(() => expect(sessionLazy.getProfileDisplayNameOnce).toHaveBeenCalled())
    })

    it('updates to ProfileMenu when Hub fires signedIn', async () => {
      let hubCallback: ((data: { payload: { event: string } }) => void) | undefined
      hubListenMock.mockImplementation((channel, cb) => {
        void channel
        hubCallback = cb
        return () => {}
      })

      auth.isAuthConfigured.mockReturnValue(true)
      sessionLazy.probeSignedIn.mockResolvedValue(true)
      api.hasSignedInIdToken.mockResolvedValue(false)

      render(
        <MemoryRouter initialEntries={['/']}>
          <StudentHeader />
        </MemoryRouter>,
      )

      expect(await screen.findByRole('link', { name: 'Sign In' })).toBeTruthy()
      expect(hubCallback).toBeDefined()

      await act(async () => {
        hubCallback!({ payload: { event: 'signedIn' } })
      })

      expect(await screen.findByRole('button', { name: /Account menu/i })).toBeTruthy()
    })

    it('probes immediately when OAuth callback query params are cleared', async () => {
      auth.isAuthConfigured.mockReturnValue(true)
      sessionLazy.probeSignedIn.mockResolvedValue(true)

      function Shell() {
        const navigate = useNavigate()
        return (
          <>
            <StudentHeader />
            <button type="button" onClick={() => navigate('/')}>
              Leave OAuth
            </button>
          </>
        )
      }

      render(
        <MemoryRouter initialEntries={['/?code=x&state=y']}>
          <Routes>
            <Route path="*" element={<Shell />} />
          </Routes>
        </MemoryRouter>,
      )

      expect(sessionLazy.probeSignedIn).not.toHaveBeenCalled()

      fireEvent.click(screen.getByRole('button', { name: 'Leave OAuth' }))

      await waitFor(() => expect(sessionLazy.probeSignedIn).toHaveBeenCalledTimes(1))
      expect(await screen.findByRole('button', { name: /Account menu/i })).toBeTruthy()
    })
  })
})
