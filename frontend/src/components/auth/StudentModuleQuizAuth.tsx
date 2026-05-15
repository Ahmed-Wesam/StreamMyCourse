import { SignIn } from './SignIn'
import ModuleQuizPage from '../../pages/ModuleQuizPage'
import { isAuthConfigured } from '../../lib/auth'

/**
 * Module quiz requires sign-in when the API uses a Cognito authorizer.
 */
export function StudentModuleQuizAuth() {
  if (!isAuthConfigured()) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-gray-700">
        Module quiz requires authentication, but Cognito environment variables are not set for this build.
      </div>
    )
  }

  return (
    <SignIn>
      <ModuleQuizPage />
    </SignIn>
  )
}
