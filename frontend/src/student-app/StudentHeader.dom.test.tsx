/**

 * @vitest-environment jsdom

 */

import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'

import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'

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



vi.mock('../lib/auth', async (importOriginal) => {

  const mod = (await importOriginal()) as typeof import('../lib/auth')

  return {

    ...mod,

    isAuthConfigured: (...args: unknown[]) =>

      auth.isAuthConfigured(...args) as ReturnType<typeof mod.isAuthConfigured>,

  }

})



vi.mock('../lib/auth-session-lazy', async (importOriginal) => {

  const mod = (await importOriginal()) as typeof import('../lib/auth-session-lazy')

  return {

    ...mod,

    probeSignedIn: (...args: unknown[]) => sessionLazy.probeSignedIn(...args),

    warmUserProfileOnce: (...args: unknown[]) => sessionLazy.warmUserProfileOnce(...args),

  }

})



vi.mock('aws-amplify/auth', () => ({

  signOut: (...args: unknown[]) => amplifyAuth.signOut(...args),

}))



vi.mock('aws-amplify/utils', () => ({

  Hub: { listen: hubListenMock },

}))



function flushRequestIdleCallbacks() {

  const pending = [...idleCallbacks]

  idleCallbacks.length = 0

  for (const cb of pending) {

    cb({ didTimeout: false, timeRemaining: () => 50 } as IdleDeadline)

  }

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



  it('renders primary navigation links', () => {

    auth.isAuthConfigured.mockReturnValue(false)

    render(

      <MemoryRouter initialEntries={['/']}>

        <StudentHeader />

      </MemoryRouter>,

    )



    expect(screen.getByRole('link', { name: 'Home' })).toBeTruthy()

    expect(screen.getByRole('link', { name: 'Details' })).toBeTruthy()

    expect(screen.getByRole('link', { name: 'Courses' })).toBeTruthy()

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

    sessionLazy.probeSignedIn.mockResolvedValue(true)

    amplifyAuth.signOut.mockResolvedValue(undefined)



    localStorage.setItem('t', '1')

    document.cookie = 'a=b'



    render(

      <MemoryRouter initialEntries={['/']}>

        <StudentHeader />

      </MemoryRouter>,

    )



    await act(async () => {

      flushRequestIdleCallbacks()

    })



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

            <Route path="/details" element={<div>Details body</div>} />

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



    fireEvent.click(within(mobileNav).getByRole('link', { name: 'Details' }))

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



    it('shows Sign out when probeSignedIn resolves true (idle probe)', async () => {

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



      expect(await screen.findByRole('button', { name: 'Sign out' })).toBeTruthy()

      expect(api.hasSignedInIdToken).not.toHaveBeenCalled()

      await waitFor(() =>
        expect(sessionLazy.warmUserProfileOnce).toHaveBeenCalledWith(true),
      )

    })



    it('updates to Sign out when Hub fires signedIn', async () => {

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



      expect(await screen.findByRole('link', { name: 'Sign in' })).toBeTruthy()

      expect(hubCallback).toBeDefined()



      await act(async () => {

        hubCallback!({ payload: { event: 'signedIn' } })

      })



      expect(await screen.findByRole('button', { name: 'Sign out' })).toBeTruthy()

    })



    it('probes immediately when OAuth callback query params are cleared', async () => {

      auth.isAuthConfigured.mockReturnValue(true)

      sessionLazy.probeSignedIn.mockResolvedValue(true)



      function Shell() {

        const navigate = useNavigate()

        return (

          <>

            <StudentHeader />

            <button type="button" onClick={() => navigate('/')}>Leave OAuth</button>

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

      expect(await screen.findByRole('button', { name: 'Sign out' })).toBeTruthy()

    })

  })

})


