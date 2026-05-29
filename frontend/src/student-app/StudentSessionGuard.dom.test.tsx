/**
 * @vitest-environment jsdom
 */
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { sessionSupersededUserMessage } from '../lib/apiUserMessages'
import {
  notifySessionSuperseded,
  resetSessionSupersededListenersForTests,
  resetSessionSupersededNotifyCooldownForTests,
} from '../lib/handleSessionSuperseded'
import { SESSION_SUPERSEDED_BANNER_KEY } from '../lib/session-superseded-banner'

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

vi.mock('../lib/student-session-refresh', () => ({
  registerStudentSessionRefreshMetadata: registerStudentSessionRefreshMetadataMock,
}))

vi.mock('aws-amplify/utils', () => ({
  Hub: { listen: hubListenMock },
}))

vi.mock('../lib/session-superseded-banner', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/session-superseded-banner')>()
  return { ...mod, SUPERSEDED_REDIRECT_DELAY_MS: 30 }
})

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

  it('calls lazySignOut, shows banner, then navigates to /login after a delay', async () => {
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

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeTruthy()
      expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()
    })
  })

  it('cancels delayed /login redirect when Hub signedIn clears the banner', async () => {
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
    hubCallback!({ payload: { event: 'signedIn' } })

    await waitFor(() => {
      expect(lazySignOutMock).toHaveBeenCalledTimes(1)
      expect(screen.queryByTestId('session-superseded-banner')).toBeNull()
    })

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100))
    })
    expect(screen.queryByTestId('login-page')).toBeNull()
    expect(screen.getByTestId('child')).toBeTruthy()
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

  it('clears banner on mount when probeSignedIn is true', async () => {
    probeSignedInMock.mockResolvedValue(true)

    renderGuard()

    await waitFor(() => {
      expect(probeSignedInMock).toHaveBeenCalled()
    })
    expect(screen.queryByTestId('session-superseded-banner')).toBeNull()
  })

  it('still shows banner and schedules redirect when lazySignOut rejects', async () => {
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

    await waitFor(() => {
      expect(screen.getByTestId('login-page')).toBeTruthy()
      expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()
    })
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
