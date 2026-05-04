import { SignIn } from './SignIn'
import LessonPlayerPage from '../../pages/LessonPlayerPage'
import { isAuthConfigured } from '../../lib/auth'

/**
 * Lesson playback requires sign-in when the API uses a Cognito authorizer.
 */
export function StudentLessonAuth() {
  if (!isAuthConfigured()) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center text-gray-700">
        Playback requires authentication, but Cognito environment variables are not set for this build.
      </div>
    )
  }

  return (
    <SignIn>
      <LessonPlayerPage />
    </SignIn>
  )
}
