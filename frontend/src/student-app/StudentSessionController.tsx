import { useEffect, useRef, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
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

type StudentSessionControllerProps = {
  onMessage: Dispatch<SetStateAction<string | null>>
}

/** Lazy-loaded session wiring (Hub, refresh metadata, superseded sign-out). */
export function StudentSessionController({ onMessage }: StudentSessionControllerProps) {
  const handlingRef = useRef(false)

  useEffect(() => {
    registerStudentSessionRefreshMetadata()
  }, [])

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
      onMessage(sessionSupersededUserMessage)
      void lazySignOut().catch(() => {
        handlingRef.current = false
      })
    })
  }, [onMessage])

  return null
}
