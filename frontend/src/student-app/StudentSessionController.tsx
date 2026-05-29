import { useEffect, useRef, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
import { Hub } from 'aws-amplify/utils'

import { sessionSupersededUserMessage } from '../lib/apiUserMessages'
import { lazySignOut, probeSignedIn } from '../lib/auth-session-lazy'
import {
  reapplySessionSupersedeGuards,
  subscribeSessionSuperseded,
} from '../lib/handleSessionSuperseded'
import { clearSessionSupersedeHandling } from '../lib/session-supersede-handling'
import { restoreStudentSessionRefreshMetadata } from '../lib/student-session-refresh'
import {
  clearSessionSupersededBanner,
  persistSessionSupersededBanner,
  readSessionSupersededBanner,
} from '../lib/session-superseded-banner'

function clearSupersededUiState(
  handlingRef: MutableRefObject<boolean>,
  setMessage: Dispatch<SetStateAction<string | null>>,
) {
  handlingRef.current = false
  clearSessionSupersedeHandling()
  restoreStudentSessionRefreshMetadata()
  clearSessionSupersededBanner()
  setMessage(null)
}

function showSupersededBanner(setMessage: Dispatch<SetStateAction<string | null>>): void {
  persistSessionSupersededBanner(sessionSupersededUserMessage)
  setMessage(sessionSupersededUserMessage)
}

function completeSupersededSignOut(
  handlingRef: MutableRefObject<boolean>,
  setMessage: Dispatch<SetStateAction<string | null>>,
  onAfterSuperseded?: () => void,
): void {
  if (!handlingRef.current) return
  showSupersededBanner(setMessage)
  onAfterSuperseded?.()
  // Allow Hub signedIn to verify a real new session; latch stays armed until then or dismiss.
  handlingRef.current = false
}

type StudentSessionControllerProps = {
  onMessage: Dispatch<SetStateAction<string | null>>
  /** Called after supersede sign-out completes (e.g. re-sync banner from sessionStorage). */
  onAfterSuperseded?: () => void
}

/** Session wiring (Hub, superseded sign-out). Refresh metadata registers in StudentSessionGuard. */
export function StudentSessionController({
  onMessage,
  onAfterSuperseded,
}: StudentSessionControllerProps) {
  const handlingRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    const hubStop = Hub.listen('auth', ({ payload }) => {
      const event = payload.event as string
      if (event === 'signedIn') {
        if (handlingRef.current) return
        void (async () => {
          const signedIn = await probeSignedIn({ bypassSupersedeLatch: true })
          if (cancelled || !signedIn) {
            if (readSessionSupersededBanner()) {
              reapplySessionSupersedeGuards()
            }
            return
          }
          clearSupersededUiState(handlingRef, onMessage)
        })()
      }
      if (event === 'signedOut') {
        handlingRef.current = false
      }
    })

    void (async () => {
      const persisted = readSessionSupersededBanner()
      if (persisted) {
        reapplySessionSupersedeGuards()
        onMessage(persisted)
        return
      }
      const signedIn = await probeSignedIn()
      if (cancelled || !signedIn || handlingRef.current) return
      clearSupersededUiState(handlingRef, onMessage)
    })()

    return () => {
      cancelled = true
      hubStop()
    }
  }, [onMessage])

  useEffect(() => {
    return subscribeSessionSuperseded(() => {
      if (handlingRef.current) return
      handlingRef.current = true
      showSupersededBanner(onMessage)
      void lazySignOut()
        .then(() => completeSupersededSignOut(handlingRef, onMessage, onAfterSuperseded))
        .catch(() => completeSupersededSignOut(handlingRef, onMessage, onAfterSuperseded))
    })
  }, [onMessage, onAfterSuperseded])

  return null
}
