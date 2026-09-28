/** Profile fields persisted across register → verify (never store passwords here). */

export const REGISTER_PROFILE_DRAFT_KEY = 'rs_register_profile_draft'

type RegisterProfileDraft = {
  email: string
  givenName: string
  familyName: string
  country: string
  profession: string
  institution: string
  researchInterests: string
  termsAccepted: boolean
  privacyAccepted: boolean
}

export function saveRegisterProfileDraft(draft: RegisterProfileDraft): void {
  sessionStorage.setItem(REGISTER_PROFILE_DRAFT_KEY, JSON.stringify(draft))
}

export function readRegisterProfileDraft(): RegisterProfileDraft | null {
  try {
    const raw = sessionStorage.getItem(REGISTER_PROFILE_DRAFT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as RegisterProfileDraft
    if (!parsed || typeof parsed !== 'object') return null
    return parsed
  } catch {
    return null
  }
}

export function clearRegisterProfileDraft(): void {
  sessionStorage.removeItem(REGISTER_PROFILE_DRAFT_KEY)
}
