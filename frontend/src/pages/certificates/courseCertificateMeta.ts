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

type BundlePathwayRow = {
  title: (typeof PATHWAY_COURSE_TITLES)[number]
  hours: number
  hoursLine: string
}

const HOURS_ASSESSMENT_SUFFIX = ' · Competency-Based Assessment'

/** Map pathway title → "N Hours · Competency-Based Assessment". */
export function durationLine(title: string): string | null {
  if (!(PATHWAY_COURSE_TITLES as readonly string[]).includes(title)) {
    return null
  }
  const hours = CERT_LEARNING_HOURS[title as (typeof PATHWAY_COURSE_TITLES)[number]]
  return `${hours} Hours${HOURS_ASSESSMENT_SUFFIX}`
}

/** Sum of CERT_LEARNING_HOURS (140). */
export function bundleTotalHours(): number {
  return PATHWAY_COURSE_TITLES.reduce((sum, title) => sum + CERT_LEARNING_HOURS[title], 0)
}

/** Pathway rows with hours and display lines from CERT_LEARNING_HOURS. */
export function bundlePathwayRows(): BundlePathwayRow[] {
  return PATHWAY_COURSE_TITLES.map((title) => {
    const hours = CERT_LEARNING_HOURS[title]
    const hoursLine = durationLine(title)
    return {
      title,
      hours,
      hoursLine: hoursLine ?? `${hours} Hours${HOURS_ASSESSMENT_SUFFIX}`,
    }
  })
}
