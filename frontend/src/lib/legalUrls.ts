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

export function termsUrl(): string {
  return `${studentSiteOrigin()}/terms`
}

export function privacyUrl(): string {
  return `${studentSiteOrigin()}/privacy`
}
