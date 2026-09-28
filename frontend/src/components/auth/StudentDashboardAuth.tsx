import { Outlet } from 'react-router-dom'

import { SignIn } from './SignIn'
import { isAuthConfigured } from '../../lib/auth'

/**
 * Student dashboard requires sign-in when the API uses a Cognito authorizer.
 */
export function StudentDashboardAuth() {
  if (!isAuthConfigured()) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-gray-700">
        Your dashboard requires authentication, but Cognito environment variables are not set for
        this build.
      </div>
    )
  }

  return (
    <SignIn>
      <Outlet />
    </SignIn>
  )
}
