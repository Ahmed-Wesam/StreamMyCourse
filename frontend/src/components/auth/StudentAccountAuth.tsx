import { Outlet } from 'react-router-dom'

import { SignIn } from './SignIn'
import { isAuthConfigured } from '../../lib/auth'

/**
 * Account area requires sign-in when the API uses a Cognito authorizer.
 */
export function StudentAccountAuth() {
  if (!isAuthConfigured()) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-gray-700">
        Account settings require authentication, but Cognito environment variables are not set for
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
