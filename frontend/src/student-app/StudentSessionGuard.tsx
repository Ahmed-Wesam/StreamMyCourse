import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { registerStudentSessionRefreshMetadata } from '../lib/student-session-refresh'
import {
  readSessionSupersededBanner,
  SUPERSEDED_REDIRECT_DELAY_MS,
} from '../lib/session-superseded-banner'
import { StudentSessionController } from './StudentSessionController'

/**
 * Student-only: wires Cognito refresh ClientMetadata and signs out when the API
 * reports session_superseded (signed in elsewhere).
 *
 * Registers refresh metadata synchronously on mount (before header idle probe).
 * Uses lazySignOut (not useAuthenticator) so public routes work without AuthShell.
 */
export function StudentSessionGuard({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(() => readSessionSupersededBanner())
  const navigate = useNavigate()
  const redirectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearSupersededRedirectTimer = useCallback(() => {
    if (redirectTimeoutRef.current != null) {
      clearTimeout(redirectTimeoutRef.current)
      redirectTimeoutRef.current = null
    }
  }, [])

  useEffect(() => {
    registerStudentSessionRefreshMetadata()
  }, [])

  useEffect(() => () => clearSupersededRedirectTimer(), [clearSupersededRedirectTimer])

  const scheduleSupersededRedirect = useCallback(() => {
    clearSupersededRedirectTimer()
    redirectTimeoutRef.current = setTimeout(() => {
      redirectTimeoutRef.current = null
      navigate('/login', { replace: true })
    }, SUPERSEDED_REDIRECT_DELAY_MS)
  }, [clearSupersededRedirectTimer, navigate])

  useEffect(() => {
    if (message == null) {
      clearSupersededRedirectTimer()
    }
  }, [message, clearSupersededRedirectTimer])

  return (
    <>
      {message ? (
        <div
          className="sticky top-16 z-[60] border-b border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm text-amber-900 shadow-sm"
          role="alert"
          data-testid="session-superseded-banner"
        >
          {message}
        </div>
      ) : null}
      <StudentSessionController
        onMessage={setMessage}
        onAfterSuperseded={scheduleSupersededRedirect}
      />
      {children}
    </>
  )
}
