/** Prototype pathway order (Certificates.html). */
export const PATHWAY_COURSE_TITLES = [
  'Research Methodology',
  'Statistics & SPSS',
  'Scientific Writing',
  'Systematic Reviews & Meta-Analysis',
] as const

/** Learning hours credited per completed course (Certificates.html CERT_HOURS). */
export const CERT_LEARNING_HOURS: Record<(typeof PATHWAY_COURSE_TITLES)[number], number> = {
  'Research Methodology': 28,
  'Statistics & SPSS': 42,
  'Scientific Writing': 32,
  'Systematic Reviews & Meta-Analysis': 38,
}

export type CourseSealKey =
  | 'research-methodology'
  | 'statistics-spss'
  | 'scientific-writing'
  | 'systematic-reviews-meta-analysis'

const TITLE_TO_SEAL: Record<(typeof PATHWAY_COURSE_TITLES)[number], CourseSealKey> = {
  'Research Methodology': 'research-methodology',
  'Statistics & SPSS': 'statistics-spss',
  'Scientific Writing': 'scientific-writing',
  'Systematic Reviews & Meta-Analysis': 'systematic-reviews-meta-analysis',
}

export function sealKeyForTitle(title: string): CourseSealKey | null {
  if ((PATHWAY_COURSE_TITLES as readonly string[]).includes(title)) {
    return TITLE_TO_SEAL[title as (typeof PATHWAY_COURSE_TITLES)[number]]
  }
  return null
}
