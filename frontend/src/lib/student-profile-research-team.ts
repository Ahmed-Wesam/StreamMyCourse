import type { UserProfile } from './api/types'

/** Country and profession on the saved profile (required before Research Team apply). */
export function hasResearchTeamProfileFields(profile: Pick<UserProfile, 'country' | 'profession'>): boolean {
  return Boolean(profile.country?.trim() && profile.profession?.trim())
}
