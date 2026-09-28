import { SignIn } from './SignIn'
import AssignmentPage from '../../pages/AssignmentPage'
import { isAuthConfigured } from '../../lib/auth'

/**
 * Assignment detail requires sign-in when the API uses a Cognito authorizer.
 */
export function StudentAssignmentAuth() {
  if (!isAuthConfigured()) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-gray-700">
        Assignments require authentication, but Cognito environment variables are not set for this build.
      </div>
    )
  }

  return (
    <SignIn>
      <AssignmentPage />
    </SignIn>
  )
}
