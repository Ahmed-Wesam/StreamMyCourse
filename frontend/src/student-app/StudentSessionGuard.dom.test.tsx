/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { sessionSupersededUserMessage } from '../lib/apiUserMessages'
import { notifySessionSuperseded, resetSessionSupersededListenersForTests } from '../lib/handleSessionSuperseded'

const lazySignOutMock = vi.hoisted(() => vi.fn().mockResolvedValue(undefined))
const probeSignedInMock = vi.hoisted(() => vi.fn().mockResolvedValue(false))
const registerStudentSessionRefreshMetadataMock = vi.hoisted(() => vi.fn())
const hubListenMock = vi.hoisted(() =>
  vi.fn((_channel: string, _cb: (data: { payload: { event: string } }) => void) => () => {}),
)

vi.mock('../lib/auth-session-lazy', () => ({
  lazySignOut: (...args: unknown[]) => lazySignOutMock(...args),
  probeSignedIn: (...args: unknown[]) => probeSignedInMock(...args),
}))

vi.mock('../lib/student-session-refresh', () => ({
  registerStudentSessionRefreshMetadata: registerStudentSessionRefreshMetadataMock,
}))

vi.mock('aws-amplify/utils', () => ({
  Hub: { listen: hubListenMock },
}))

import { StudentSessionGuard } from './StudentSessionGuard'

describe('StudentSessionGuard', () => {
  afterEach(() => {
    cleanup()
    resetSessionSupersededListenersForTests()
    lazySignOutMock.mockClear()
    probeSignedInMock.mockReset()
    probeSignedInMock.mockResolvedValue(false)
    registerStudentSessionRefreshMetadataMock.mockClear()
  })

  it('registers student refresh metadata on mount without AuthenticatorProvider', () => {
    render(
      <StudentSessionGuard>
        <div data-testid="child" />
      </StudentSessionGuard>,
    )
    expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('child')).toBeTruthy()
  })

  it('calls lazySignOut and shows banner on session_superseded', async () => {
    render(
      <StudentSessionGuard>
        <div data-testid="child" />
      </StudentSessionGuard>,
    )

    notifySessionSuperseded()

    await waitFor(() => {
      expect(lazySignOutMock).toHaveBeenCalledTimes(1)
    })
    expect(screen.getByTestId('session-superseded-banner').textContent).toContain(sessionSupersededUserMessage)
  })

  it('clears banner and re-arms handler after Hub signedIn', async () => {
    let hubCallback: ((data: { payload: { event: string } }) => void) | undefined
    hubListenMock.mockImplementation(
      (_channel: string, cb: (data: { payload: { event: string } }) => void) => {
        hubCallback = cb
        return () => {}
      },
    )

    render(
      <StudentSessionGuard>
        <div data-testid="child" />
      </StudentSessionGuard>,
    )

    expect(hubListenMock).toHaveBeenCalledWith('auth', expect.any(Function))
    expect(hubCallback).toBeDefined()

    notifySessionSuperseded()
    await waitFor(() => expect(lazySignOutMock).toHaveBeenCalledTimes(1))
    expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()

    hubCallback!({ payload: { event: 'signedIn' } })

    await waitFor(() => {
      expect(screen.queryByTestId('session-superseded-banner')).toBeNull()
    })

    lazySignOutMock.mockClear()
    notifySessionSuperseded()
    await waitFor(() => expect(lazySignOutMock).toHaveBeenCalledTimes(1))
  })

  it('does not call lazySignOut twice while supersede handling is in flight', async () => {
    lazySignOutMock.mockImplementation(
      () => new Promise<void>((resolve) => setTimeout(resolve, 50)),
    )

    render(
      <StudentSessionGuard>
        <div data-testid="child" />
      </StudentSessionGuard>,
    )

    notifySessionSuperseded()
    notifySessionSuperseded()

    await waitFor(() => expect(lazySignOutMock).toHaveBeenCalledTimes(1))
  })

  it('clears banner on mount when probeSignedIn is true', async () => {
    probeSignedInMock.mockResolvedValue(true)

    render(
      <StudentSessionGuard>
        <div data-testid="child" />
      </StudentSessionGuard>,
    )

    await waitFor(() => {
      expect(probeSignedInMock).toHaveBeenCalled()
    })
    expect(screen.queryByTestId('session-superseded-banner')).toBeNull()
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

    render(
      <StudentSessionGuard>
        <div data-testid="child" />
      </StudentSessionGuard>,
    )

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
