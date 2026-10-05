import { fetchMe, patchUsersMe } from './api/session'
import type { UserProfile } from './api/types'
import { clearGoogleOAuthTermsAck, readGoogleOAuthTermsAck } from './google-oauth-terms'
import { clearRegisterProfileDraft, readRegisterProfileDraft } from './register-profile-draft'

function registerDraftMatchesProfile(
  draft: NonNullable<ReturnType<typeof readRegisterProfileDraft>>,
  me: UserProfile,
): boolean {
  const draftEmail = draft.email?.trim()
  if (!draftEmail) return true
  return draftEmail.toLowerCase() === (me.email ?? '').trim().toLowerCase()
}

function mergedProfileFields(
  me: UserProfile,
  draft: ReturnType<typeof readRegisterProfileDraft>,
): {
  givenName: string
  familyName: string
  country: string
  profession: string
  institution: string | undefined
  researchInterests: string | undefined
} {
  const useDraft = draft && registerDraftMatchesProfile(draft, me)
  const pick = (fromMe: string | undefined, fromDraft: string | undefined) =>
    fromMe?.trim() || (useDraft ? fromDraft?.trim() : '') || ''

  const institution = pick(me.institution, draft?.institution)
  const researchInterests = pick(me.researchInterests, draft?.researchInterests)

  return {
    givenName: pick(me.givenName, draft?.givenName),
    familyName: pick(me.familyName, draft?.familyName),
    country: pick(me.country, draft?.country),
    profession: pick(me.profession, draft?.profession),
    institution: institution || undefined,
    researchInterests: researchInterests || undefined,
  }
}

/**
 * After Google OAuth, persist terms timestamps when the user accepted them before redirect
 * and country/profession are available (RDS profile and/or register form draft).
 */
export async function applyGoogleOAuthTermsAckIfNeeded(me?: UserProfile): Promise<void> {
  const ack = readGoogleOAuthTermsAck()
  if (!ack) return

  const profile = me ?? (await fetchMe())
  if (profile.termsAcceptedAt?.trim() && profile.privacyAcceptedAt?.trim()) {
    clearGoogleOAuthTermsAck()
    clearRegisterProfileDraft()
    return
  }

  const draft = readRegisterProfileDraft()
  const fields = mergedProfileFields(profile, draft)
  const { country, profession } = fields
  if (!country || !profession) {
    return
  }

  await patchUsersMe({
    givenName: fields.givenName,
    familyName: fields.familyName,
    country,
    profession,
    institution: fields.institution,
    researchInterests: fields.researchInterests,
    termsAcceptedAt: ack.termsAcceptedAt,
    privacyAcceptedAt: ack.privacyAcceptedAt,
  })
  clearGoogleOAuthTermsAck()
  clearRegisterProfileDraft()
}
