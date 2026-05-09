/**
 * Thin placeholders for fields the catalog API does not expose yet.
 * Each use site must keep an adjacent TODO anchor (format: `TODO(figma-backend) GAP-…:`)
 * and a row in
 * `reports/figma-student-ui-gap-report.md`.
 */
import instructorImageSrc from '../assets/instructors/dr-bahaa-aburayya.png'
export const FIGMA_MOCK_CATALOG_COURSE_PACING = 'Self-paced (sample)'

export const FIGMA_MOCK_COURSE_INSTRUCTOR_NAME = 'Dr. Bahaa Aburayya'

/** Local placeholder used until the catalog API exposes an instructor image field. */
export const FIGMA_MOCK_COURSE_INSTRUCTOR_IMAGE_SRC = instructorImageSrc

export const FIGMA_MOCK_COURSE_PRICING_PLANS = [
  {
    id: '1month',
    duration: '1 Month',
    price: 50,
    billing: 'Billed once',
    savings: null as number | null,
    savingsPct: null as string | null,
    perMonth: 50,
    highlight: false,
    badge: null as string | null,
    perks: [
      'Full access to all modules',
      'HD video lessons',
      'Practice datasets',
      'Community forum access',
      'Certificate of completion',
      '7-day money-back guarantee',
    ],
  },
  {
    id: '3month',
    duration: '3 Months',
    price: 75,
    billing: 'Billed once',
    savings: 75,
    savingsPct: '50%',
    perMonth: 25,
    highlight: true,
    badge: 'Most Popular',
    perks: [
      'Full access to all modules',
      'HD video lessons',
      'Practice datasets',
      'Community forum access',
      'Certificate of completion',
      '7-day money-back guarantee',
      'Live Q&A sessions (sample)',
    ],
  },
  {
    id: '6month',
    duration: '6 Months',
    price: 100,
    billing: 'Billed once',
    savings: 200,
    savingsPct: '67%',
    perMonth: 17,
    highlight: false,
    badge: 'Best Value',
    perks: [
      'Full access to all modules',
      'HD video lessons',
      'Practice datasets',
      'Community forum access',
      'Certificate of completion',
      '7-day money-back guarantee',
      'Live Q&A sessions (sample)',
      'Priority email support (sample)',
      'Bonus module (sample)',
    ],
  },
] as const
