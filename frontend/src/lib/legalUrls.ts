import { legalConfig } from './legalConfig'

const DEFAULT_STUDENT_ORIGIN = `https://${legalConfig.websiteHost}`

/** Student SPA origin for absolute legal links (PayTabs, footers). */
export function studentSiteOrigin(): string {
  const env = import.meta.env.VITE_STUDENT_SITE_URL
  if (typeof env === 'string' && env.trim().length > 0) {
    return env.trim().replace(/\/+$/, '')
  }
  return DEFAULT_STUDENT_ORIGIN
}

function legalPath(path: string): string {
  return `${studentSiteOrigin()}${path}`
}

export function termsUrl(): string {
  return legalPath('/terms')
}

export function privacyUrl(): string {
  return legalPath('/privacy')
}

export function refundUrl(): string {
  return legalPath('/refund')
}

export function deliveryUrl(): string {
  return legalPath('/delivery')
}

export function educationalDisclaimerUrl(): string {
  return legalPath('/educational-disclaimer')
}
