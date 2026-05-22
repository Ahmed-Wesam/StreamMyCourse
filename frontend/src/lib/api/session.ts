import { fetchAuthSession } from 'aws-amplify/auth'

import { isAuthConfigured } from '../auth'
import { bearerFromSession, httpGet } from './client'
import type { UserProfile } from './types'

/** True when Cognito is configured and the user has an ID token (signed in). */
export async function hasSignedInIdToken(): Promise<boolean> {
  if (!isAuthConfigured()) return false
  try {
    const session = await fetchAuthSession()
    return Boolean(bearerFromSession(session))
  } catch {
    return false
  }
}

export async function fetchMe(): Promise<UserProfile> {
  return httpGet<UserProfile>('/users/me')
}
