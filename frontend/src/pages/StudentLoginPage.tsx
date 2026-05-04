import { useAuthenticator } from '@aws-amplify/ui-react'
import { Navigate } from 'react-router-dom'

import { SignIn } from '../components/auth/SignIn'
import { isAuthConfigured } from '../lib/auth'

export default function StudentLoginPage() {
  const authConfigured = isAuthConfigured()
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus])

  if (!authConfigured) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-gray-700">
        Sign-in is not available: set Cognito <code className="rounded bg-gray-100 px-1">VITE_*</code> variables for this
        SPA.
      </div>
    )
  }

  if (authStatus === 'authenticated') {
    return <Navigate to="/" replace />
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-4 py-12">
      <SignIn />
    </div>
  )
}
