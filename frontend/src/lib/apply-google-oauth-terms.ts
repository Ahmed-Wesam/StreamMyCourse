import { patchUsersMe, fetchMe } from './api/session'
import { clearGoogleOAuthTermsAck, readGoogleOAuthTermsAck } from './google-oauth-terms'

/**
 * After Google OAuth, persist terms timestamps when the user accepted them before redirect
 * and the RDS profile has country/profession (required for PATCH /users/me).
 */
export async function applyGoogleOAuthTermsAckIfNeeded(): Promise<void> {
  const ack = readGoogleOAuthTermsAck()
  if (!ack) return

  const me = await fetchMe()
  if (me.termsAcceptedAt?.trim() && me.privacyAcceptedAt?.trim()) {
    clearGoogleOAuthTermsAck()
    return
  }

  const country = me.country?.trim()
  const profession = me.profession?.trim()
  if (!country || !profession) {
    return
  }

  await patchUsersMe({
    givenName: me.givenName?.trim() ?? '',
    familyName: me.familyName?.trim() ?? '',
    country,
    profession,
    institution: me.institution?.trim() || undefined,
    researchInterests: me.researchInterests?.trim() || undefined,
    termsAcceptedAt: ack.termsAcceptedAt,
    privacyAcceptedAt: ack.privacyAcceptedAt,
  })
  clearGoogleOAuthTermsAck()
}
