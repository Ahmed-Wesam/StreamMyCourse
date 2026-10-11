import { legalConfig } from './legalConfig'

const DEFAULT_STUDENT_ORIGIN = `https://${legalConfig.websiteHost}`

/** Student site origin for absolute legal links in the teacher shell. */
export function studentSiteOrigin(): string {
  const env = import.meta.env.VITE_STUDENT_SITE_URL
  if (typeof env === 'string' && env.trim().length > 0) {
    return env.trim().replace(/\/+$/, '')
  }
  return DEFAULT_STUDENT_ORIGIN
}

