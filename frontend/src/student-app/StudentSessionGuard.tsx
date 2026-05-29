import {
  Children,
  cloneElement,
  isValidElement,
  useCallback,
  useEffect,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react'

import { Layout } from '../components/layout/Layout'
import { registerStudentSessionRefreshMetadata } from '../lib/student-session-refresh'
import {
  dismissSessionSupersededBannerUi,
  readSessionSupersededBanner,
} from '../lib/session-superseded-banner'
import { SessionSupersededBanner } from './SessionSupersededBanner'
import { StudentSessionController } from './StudentSessionController'

function injectLayoutChromeAlert(children: ReactNode, alert: ReactNode): ReactNode {
  const only = Children.only(children)
  if (!isValidElement(only) || only.type !== Layout) {
    return (
      <>
        {alert}
        {children}
      </>
    )
  }
  const layout = only as ReactElement<{ chromeAlert?: ReactNode }>
  return cloneElement(layout, {
    chromeAlert: (
      <>
        {layout.props.chromeAlert}
        {alert}
      </>
    ),
  })
}

/**
 * Student-only: wires Cognito refresh ClientMetadata and signs out when the API
 * reports session_superseded (signed in elsewhere).
 *
 * Registers refresh metadata synchronously on mount (before header idle probe).
 * Uses lazySignOut (not useAuthenticator) so public routes work without AuthShell.
 */
export function StudentSessionGuard({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(() => readSessionSupersededBanner())

  const syncBannerFromStorage = useCallback(() => {
    setMessage(readSessionSupersededBanner())
  }, [])

  const dismissBanner = useCallback(() => {
    dismissSessionSupersededBannerUi()
    setMessage(null)
  }, [])

  useEffect(() => {
    registerStudentSessionRefreshMetadata()
  }, [])

  const alert = message ? (
    <SessionSupersededBanner message={message} onDismiss={dismissBanner} />
  ) : null

  return (
    <>
      <StudentSessionController onMessage={setMessage} onAfterSuperseded={syncBannerFromStorage} />
      {injectLayoutChromeAlert(children, alert)}
    </>
  )
}
