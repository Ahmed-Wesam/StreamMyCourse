import { lazy, Suspense, useState, type ReactNode } from 'react'

const StudentSessionController = lazy(() =>
  import('./StudentSessionController').then((m) => ({ default: m.StudentSessionController })),
)

/**
 * Student-only: wires Cognito refresh ClientMetadata and signs out when the API
 * reports session_superseded (signed in elsewhere).
 *
 * Uses lazySignOut (not useAuthenticator) so public routes work without AuthShell.
 */
export function StudentSessionGuard({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null)

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
      <Suspense fallback={null}>
        <StudentSessionController onMessage={setMessage} />
      </Suspense>
      {children}
    </>
  )
}
