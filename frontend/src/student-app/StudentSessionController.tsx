import { useEffect, useRef, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
import { Hub } from 'aws-amplify/utils'

import { sessionSupersededUserMessage } from '../lib/apiUserMessages'
import { lazySignOut, probeSignedIn } from '../lib/auth-session-lazy'
import {
  exitSupersededState,
  subscribeSessionSuperseded,
  syncSupersededFromStorage,
} from '../lib/student-session-superseded'
import { readSessionSupersededBanner } from '../lib/session-superseded-banner'

function clearSupersededUiState(
  handlingRef: MutableRefObject<boolean>,
  setMessage: Dispatch<SetStateAction<string | null>>,
) {
  handlingRef.current = false
  exitSupersededState()
  setMessage(null)
}

function showSupersededBanner(setMessage: Dispatch<SetStateAction<string | null>>): void {
  setMessage(readSessionSupersededBanner() ?? sessionSupersededUserMessage)
}

function completeSupersededSignOut(
  handlingRef: MutableRefObject<boolean>,
  onAfterSuperseded?: () => void,
): void {
  if (!handlingRef.current) return
  onAfterSuperseded?.()
  // Allow Hub signedIn to verify a real new session; supersede state stays active until then or dismiss.
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
          const signedIn = await probeSignedIn({ bypassSupersedeCheck: true })
          if (cancelled || !signedIn) {
            if (readSessionSupersededBanner()) {
              syncSupersededFromStorage()
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
        syncSupersededFromStorage()
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
        .then(() => completeSupersededSignOut(handlingRef, onAfterSuperseded))
        .catch(() => completeSupersededSignOut(handlingRef, onAfterSuperseded))
    })
  }, [onMessage, onAfterSuperseded])

  return null
}
