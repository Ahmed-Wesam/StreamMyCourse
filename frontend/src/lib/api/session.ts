import { fetchAuthSession } from 'aws-amplify/auth'

import { isAuthConfigured } from '../auth'
import { isCognitoRefreshSessionSupersededError } from '../cognito-session-superseded'
import { notifySessionSuperseded } from '../handleSessionSuperseded'
import { isSessionSupersedeHandling } from '../session-supersede-handling'
import { bearerFromSession, httpGet } from './client'
import type { UserProfile } from './types'

/** True when Cognito is configured and the user has an ID token (signed in). */
export async function hasSignedInIdToken(): Promise<boolean> {
  if (!isAuthConfigured()) return false
  if (isSessionSupersedeHandling()) return false
  try {
    const session = await fetchAuthSession()
    return Boolean(bearerFromSession(session))
  } catch (error) {
    if (isCognitoRefreshSessionSupersededError(error)) {
      notifySessionSuperseded()
    }
    return false
  }
}

export async function fetchMe(): Promise<UserProfile> {
  return httpGet<UserProfile>('/users/me')
}
