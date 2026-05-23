import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type ReactNode,
  type SetStateAction,
} from 'react'
import { Hub } from 'aws-amplify/utils'

import { sessionSupersededUserMessage } from '../lib/apiUserMessages'
import { lazySignOut, probeSignedIn } from '../lib/auth-session-lazy'
import { subscribeSessionSuperseded } from '../lib/handleSessionSuperseded'
import { registerStudentSessionRefreshMetadata } from '../lib/student-session-refresh'

function clearSupersededUiState(
  handlingRef: MutableRefObject<boolean>,
  setMessage: Dispatch<SetStateAction<string | null>>,
) {
  handlingRef.current = false
  setMessage(null)
}

/**
 * Student-only: wires Cognito refresh ClientMetadata and signs out when the API
 * reports session_superseded (signed in elsewhere).
 *
 * Uses lazySignOut (not useAuthenticator) so public routes work without AuthShell.
 */
export function StudentSessionGuard({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null)
  const handlingRef = useRef(false)

  useEffect(() => {
    registerStudentSessionRefreshMetadata()
  }, [])

  useEffect(() => {
    let cancelled = false
    const hubStop = Hub.listen('auth', ({ payload }) => {
      const event = payload.event as string
      if (event === 'signedIn') {
        clearSupersededUiState(handlingRef, setMessage)
      }
      if (event === 'signedOut') {
        handlingRef.current = false
      }
    })

    void (async () => {
      const signedIn = await probeSignedIn()
      if (cancelled || !signedIn || handlingRef.current) return
      clearSupersededUiState(handlingRef, setMessage)
    })()

    return () => {
      cancelled = true
      hubStop()
    }
  }, [])

  useEffect(() => {
    return subscribeSessionSuperseded(() => {
      if (handlingRef.current) return
      handlingRef.current = true
      setMessage(sessionSupersededUserMessage)
      void lazySignOut().catch(() => {
        handlingRef.current = false
      })
    })
  }, [])

  return (
    <>
      {message ? (
        <div
          className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm text-amber-900"
          role="alert"
          data-testid="session-superseded-banner"
        >
          {message}
        </div>
      ) : null}
      {children}
    </>
  )
}
