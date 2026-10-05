/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as session from './api/session'
import type { UserProfile } from './api/types'
import { applyGoogleOAuthTermsAckIfNeeded } from './apply-google-oauth-terms'
import { GOOGLE_OAUTH_TERMS_ACK_KEY } from './google-oauth-terms'
import { REGISTER_PROFILE_DRAFT_KEY } from './register-profile-draft'

const baseMe: UserProfile = {
  userId: 'u1',
  email: 'student@example.com',
  role: 'student',
  cognitoSub: 'u1',
  createdAt: '',
  updatedAt: '',
}

describe('applyGoogleOAuthTermsAckIfNeeded', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    sessionStorage.clear()
  })

  it('patches terms using register draft country/profession when RDS profile is empty', async () => {
    sessionStorage.setItem(
      GOOGLE_OAUTH_TERMS_ACK_KEY,
      JSON.stringify({ termsAcceptedAt: '2020-01-01T00:00:00.000Z', privacyAcceptedAt: '2020-01-01T00:00:00.000Z' }),
    )
    sessionStorage.setItem(
      REGISTER_PROFILE_DRAFT_KEY,
      JSON.stringify({
        email: 'student@example.com',
        givenName: 'Ada',
        familyName: 'Lovelace',
        country: 'United Kingdom',
        profession: 'Researcher',
        institution: '',
        researchInterests: '',
        termsAccepted: true,
        privacyAccepted: true,
      }),
    )

    const patchUsersMe = vi.spyOn(session, 'patchUsersMe').mockResolvedValue({ ...baseMe })
    const fetchMe = vi.spyOn(session, 'fetchMe')

    await applyGoogleOAuthTermsAckIfNeeded({ ...baseMe })

    expect(fetchMe).not.toHaveBeenCalled()
    expect(patchUsersMe).toHaveBeenCalledWith(
      expect.objectContaining({
        country: 'United Kingdom',
        profession: 'Researcher',
        givenName: 'Ada',
        familyName: 'Lovelace',
        termsAcceptedAt: '2020-01-01T00:00:00.000Z',
        privacyAcceptedAt: '2020-01-01T00:00:00.000Z',
      }),
    )
    expect(sessionStorage.getItem(GOOGLE_OAUTH_TERMS_ACK_KEY)).toBeNull()
    expect(sessionStorage.getItem(REGISTER_PROFILE_DRAFT_KEY)).toBeNull()
  })

  it('does not use draft when draft email does not match profile email', async () => {
    sessionStorage.setItem(
      GOOGLE_OAUTH_TERMS_ACK_KEY,
      JSON.stringify({ termsAcceptedAt: '2020-01-01T00:00:00.000Z', privacyAcceptedAt: '2020-01-01T00:00:00.000Z' }),
    )
    sessionStorage.setItem(
      REGISTER_PROFILE_DRAFT_KEY,
      JSON.stringify({
        email: 'other@example.com',
        givenName: '',
        familyName: '',
        country: 'United Kingdom',
        profession: 'Researcher',
        institution: '',
        researchInterests: '',
        termsAccepted: true,
        privacyAccepted: true,
      }),
    )

    const patchUsersMe = vi.spyOn(session, 'patchUsersMe')
    await applyGoogleOAuthTermsAckIfNeeded({ ...baseMe })

    expect(patchUsersMe).not.toHaveBeenCalled()
    expect(sessionStorage.getItem(GOOGLE_OAUTH_TERMS_ACK_KEY)).not.toBeNull()
  })
})
