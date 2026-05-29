import { useEffect, useRef, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
import { Hub } from 'aws-amplify/utils'

import { sessionSupersededUserMessage } from '../lib/apiUserMessages'
import { lazySignOut, probeSignedIn } from '../lib/auth-session-lazy'
import { subscribeSessionSuperseded } from '../lib/handleSessionSuperseded'
import {
  clearSessionSupersededBanner,
  persistSessionSupersededBanner,
} from '../lib/session-superseded-banner'

function clearSupersededUiState(
  handlingRef: MutableRefObject<boolean>,
  setMessage: Dispatch<SetStateAction<string | null>>,
) {
  handlingRef.current = false
  clearSessionSupersededBanner()
  setMessage(null)
}

type StudentSessionControllerProps = {
  onMessage: Dispatch<SetStateAction<string | null>>
  /** Called after supersede sign-out completes (e.g. delayed redirect to /login). */
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
        clearSupersededUiState(handlingRef, onMessage)
      }
      if (event === 'signedOut') {
        handlingRef.current = false
      }
    })

    void (async () => {
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
      persistSessionSupersededBanner(sessionSupersededUserMessage)
      onMessage(sessionSupersededUserMessage)
      void lazySignOut()
        .then(() => {
          // lazySignOut clears sessionStorage; restore banner for /login and remounts.
          persistSessionSupersededBanner(sessionSupersededUserMessage)
          onAfterSuperseded?.()
        })
        .catch(() => {
          handlingRef.current = false
          persistSessionSupersededBanner(sessionSupersededUserMessage)
          onAfterSuperseded?.()
        })
    })
  }, [onMessage, onAfterSuperseded])

  return null
}
