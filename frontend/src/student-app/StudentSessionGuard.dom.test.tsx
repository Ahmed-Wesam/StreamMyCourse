/**

 * @vitest-environment jsdom

 */

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'

import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'



import { sessionSupersededUserMessage } from '../lib/apiUserMessages'

import {

  notifySessionSuperseded,

  resetSessionSupersededListenersForTests,

  resetSessionSupersededNotifyCooldownForTests,

} from '../lib/handleSessionSuperseded'

import {
  isSessionSupersedeHandling,
  resetSessionSupersedeHandlingForTests,
} from '../lib/session-supersede-handling'
import {
  resetSessionSupersededDismissListenersForTests,
  SESSION_SUPERSEDED_BANNER_KEY,
} from '../lib/session-superseded-banner'



const lazySignOutMock = vi.hoisted(() =>

  vi.fn(async () => {

    const { clearClientAuthState } = await import('../lib/clear-client-auth-state')

    clearClientAuthState()

  }),

)

const probeSignedInMock = vi.hoisted(() => vi.fn().mockResolvedValue(false))

const registerStudentSessionRefreshMetadataMock = vi.hoisted(() => vi.fn())

const hubListenMock = vi.hoisted(() => vi.fn().mockReturnValue(() => {}))



vi.mock('../lib/auth-session-lazy', () => ({

  lazySignOut: () => lazySignOutMock(),

  probeSignedIn: () => probeSignedInMock(),

}))



vi.mock('../lib/student-session-refresh', async (importOriginal) => {

  const mod = await importOriginal<typeof import('../lib/student-session-refresh')>()

  return {

    ...mod,

    registerStudentSessionRefreshMetadata: registerStudentSessionRefreshMetadataMock,

  }

})



vi.mock('aws-amplify/utils', () => ({

  Hub: { listen: hubListenMock },

}))



import { StudentSessionGuard } from './StudentSessionGuard'



function renderGuard(initialPath = '/') {

  return render(

    <MemoryRouter initialEntries={[initialPath]}>

      <StudentSessionGuard>

        <Routes>

          <Route path="/login" element={<div data-testid="login-page" />} />

          <Route path="*" element={<div data-testid="child" />} />

        </Routes>

      </StudentSessionGuard>

    </MemoryRouter>,

  )

}



describe('StudentSessionGuard', () => {

  beforeEach(() => {

    resetSessionSupersededNotifyCooldownForTests()

  })



  afterEach(() => {

    cleanup()

    vi.useRealTimers()

    sessionStorage.clear()

    resetSessionSupersededListenersForTests()
    resetSessionSupersededDismissListenersForTests()
    resetSessionSupersedeHandlingForTests()

    lazySignOutMock.mockClear()

    probeSignedInMock.mockReset()

    probeSignedInMock.mockResolvedValue(false)

    registerStudentSessionRefreshMetadataMock.mockClear()

  })



  it('registers student refresh metadata on mount without AuthenticatorProvider', async () => {

    renderGuard()

    expect(screen.getByTestId('child')).toBeTruthy()

    await waitFor(() => {

      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)

    })

  })



  it('calls lazySignOut and keeps the supersede banner visible (no auto-redirect)', async () => {

    renderGuard('/courses')



    await waitFor(() => {

      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)

    })



    notifySessionSuperseded()



    await waitFor(() => {

      expect(lazySignOutMock).toHaveBeenCalledTimes(1)

      const banner = screen.getByTestId('session-superseded-banner')

      expect(banner.textContent).toContain(sessionSupersededUserMessage)

    })

    expect(sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)).toBe(

      sessionSupersededUserMessage,

    )



    await act(async () => {

      await new Promise((resolve) => setTimeout(resolve, 200))

    })

    expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()

    expect(screen.queryByTestId('login-page')).toBeNull()

    expect(screen.getByTestId('child')).toBeTruthy()

  })



  it('cancels banner when Hub signedIn clears the banner', async () => {

    let hubCallback: ((data: { payload: { event: string } }) => void) | undefined

    hubListenMock.mockImplementation((channel, cb) => {

      void channel

      hubCallback = cb

      return () => {}

    })



    renderGuard('/courses')



    await waitFor(() => {

      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)

    })



    notifySessionSuperseded()

    await waitFor(() => expect(lazySignOutMock).toHaveBeenCalledTimes(1))



    probeSignedInMock.mockResolvedValueOnce(true)
    hubCallback!({ payload: { event: 'signedIn' } })

    await waitFor(() => {
      expect(screen.queryByTestId('session-superseded-banner')).toBeNull()
    })
    expect(screen.queryByTestId('login-page')).toBeNull()
  })



  it('clears banner and re-arms handler after Hub signedIn', async () => {

    let hubCallback: ((data: { payload: { event: string } }) => void) | undefined

    hubListenMock.mockImplementation((channel, cb) => {

      void channel

      hubCallback = cb

      return () => {}

    })



    renderGuard()



    await waitFor(() => {

      expect(hubListenMock).toHaveBeenCalledWith('auth', expect.any(Function))

    })

    expect(hubCallback).toBeDefined()



    notifySessionSuperseded()

    await waitFor(() => {

      expect(lazySignOutMock).toHaveBeenCalledTimes(1)

      expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()

    })



    probeSignedInMock.mockResolvedValueOnce(true)
    hubCallback!({ payload: { event: 'signedIn' } })

    await waitFor(() => {
      expect(screen.queryByTestId('session-superseded-banner')).toBeNull()
    })

    lazySignOutMock.mockClear()

    resetSessionSupersededNotifyCooldownForTests()

    notifySessionSuperseded()

    await waitFor(() => expect(lazySignOutMock).toHaveBeenCalledTimes(1))

  })



  it('does not call lazySignOut twice while supersede handling is in flight', async () => {

    lazySignOutMock.mockImplementation(

      () => new Promise<void>((resolve) => setTimeout(resolve, 50)),

    )



    renderGuard()



    await waitFor(() => {

      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)

    })



    notifySessionSuperseded()

    notifySessionSuperseded()



    await waitFor(() => expect(lazySignOutMock).toHaveBeenCalledTimes(1))

  })



  it('clears banner on mount when probeSignedIn is true and no persisted supersede message', async () => {

    probeSignedInMock.mockResolvedValue(true)



    renderGuard()



    await waitFor(() => {

      expect(probeSignedInMock).toHaveBeenCalled()

    })

    expect(screen.queryByTestId('session-superseded-banner')).toBeNull()

  })



  it('dismisses the banner and clears sessionStorage when the side control is clicked', async () => {
    renderGuard()

    await waitFor(() => {
      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)
    })

    notifySessionSuperseded()
    await waitFor(() => {
      expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()
    })

    fireEvent.click(screen.getByTestId('session-superseded-banner-dismiss'))

    expect(screen.queryByTestId('session-superseded-banner')).toBeNull()
    expect(sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)).toBeNull()
  })

  it('keeps persisted supersede banner on mount and re-arms supersede guards', async () => {
    sessionStorage.setItem(SESSION_SUPERSEDED_BANNER_KEY, sessionSupersededUserMessage)
    probeSignedInMock.mockResolvedValue(true)

    renderGuard()

    await waitFor(() => {
      expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()
    })
    expect(probeSignedInMock).not.toHaveBeenCalled()
    expect(isSessionSupersedeHandling()).toBe(true)
  })

  it('re-arms supersede guards when Hub signedIn fires but probe is false', async () => {
    let hubCallback: ((data: { payload: { event: string } }) => void) | undefined
    hubListenMock.mockImplementation((channel, cb) => {
      void channel
      hubCallback = cb
      return () => {}
    })

    renderGuard()
    await waitFor(() => {
      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)
    })

    notifySessionSuperseded()
    await waitFor(() => expect(lazySignOutMock).toHaveBeenCalledTimes(1))
    expect(isSessionSupersedeHandling()).toBe(true)

    probeSignedInMock.mockResolvedValueOnce(false)
    hubCallback!({ payload: { event: 'signedIn' } })

    await waitFor(() => {
      expect(probeSignedInMock).toHaveBeenCalled()
      expect(isSessionSupersedeHandling()).toBe(true)
    })
    expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()
  })



  it('still shows banner when lazySignOut rejects', async () => {

    lazySignOutMock.mockRejectedValueOnce(new Error('signOut failed'))



    renderGuard('/courses')



    await waitFor(() => {

      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)

    })



    notifySessionSuperseded()



    await waitFor(() => {

      expect(lazySignOutMock).toHaveBeenCalledTimes(1)

      expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()

      expect(sessionStorage.getItem(SESSION_SUPERSEDED_BANNER_KEY)).toBe(

        sessionSupersededUserMessage,

      )

    })



    await act(async () => {

      await new Promise((resolve) => setTimeout(resolve, 200))

    })

    expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()

    expect(screen.queryByTestId('login-page')).toBeNull()

  })



  it('keeps superseded banner when probeSignedIn resolves during handling', async () => {

    let resolveProbe: (signedIn: boolean) => void = () => {}

    probeSignedInMock.mockImplementation(

      () =>

        new Promise<boolean>((resolve) => {

          resolveProbe = resolve

        }),

    )

    lazySignOutMock.mockImplementation(() => new Promise(() => {}))



    renderGuard()



    await waitFor(() => {

      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)

    })



    notifySessionSuperseded()

    await waitFor(() => {

      expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()

    })



    resolveProbe(true)

    await waitFor(() => expect(probeSignedInMock).toHaveBeenCalled())



    expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()

    expect(lazySignOutMock).toHaveBeenCalledTimes(1)

  })

})


