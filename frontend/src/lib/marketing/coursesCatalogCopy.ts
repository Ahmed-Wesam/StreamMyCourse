/** Static courses catalog marketing copy (no JSX). */

export const coursesCatalogHero = {
  headlineBefore: 'Choose Your ',
  headlineHighlight: 'Learning Path',
  sub: "Whether you're starting your first research project or refining advanced skills, Research Spectrum provides a structured pathway toward independent research.",
  primaryCta: 'Explore Courses',
  secondaryCta: 'Research Mastery Bundle',
} as const

export const coursesCatalogGrid = {
  kicker: 'All Courses',
  title: 'Choose Your Research Path',
  lead: 'Take a single course to sharpen one skill, or get the complete bundle and follow the full path to independent research.',
  emptyMessage: 'Courses will appear here',
  retryLabel: 'Try again',
  pricingPrimary: 'One-time',
  pricingSecondary: 'Lifetime access',
  viewCourse: 'View Course',
  viewCurriculum: 'View Curriculum',
  keySkillsLabel: 'Key skills',
} as const

export const coursesCatalogCompare = {
  kicker: 'Compare',
  title: 'Compare Courses',
  lead: 'See what each course covers — and how the bundle brings the full path together, including Research Team eligibility.',
  featureColumn: 'Feature',
  bundleColumn: 'Bundle',
  features: [
    'Study Design',
    'Biostatistics',
    'SPSS',
    'Manuscript Writing',
    'Journal Submission',
    'Systematic Reviews',
    'Meta-Analysis',
    'Templates',
    'Assignments',
    'Certificate',
    'Research Team Eligibility',
  ],
} as const

export const coursesCatalogJourney = {
  kicker: 'The Sequence',
  title: 'Recommended Learning Path',
  lead: 'A structured progression designed to take you from beginner to independent researcher.',
  pathNote:
    'Students can take courses individually. However, this sequence is the recommended progression for learners who want to become independent researchers.',
  steps: [
    { num: 'STEP 01', title: 'Research Methodology', final: false },
    { num: 'STEP 02', title: 'Statistics & SPSS', final: false },
    { num: 'STEP 03', title: 'Scientific Writing', final: false },
    { num: 'STEP 04', title: 'Systematic Reviews & Meta-Analysis', final: false },
    { num: 'GOAL', title: 'Research Team Eligibility', final: true },
  ],
} as const

export const coursesCatalogBundle = {
  bestTag: 'Best Value',
  title: 'Research Mastery Bundle',
  blurb:
    'Everything you need to go from your first research question to a published paper — and become eligible for the Research Spectrum Research Team.',
  includes: [
    'All Four Courses',
    'Lifetime Access',
    'Assignments',
    'Certificates',
    'Research Team Eligibility',
  ],
  programLabel: 'Complete Program',
  accessLabel: 'Lifetime access',
  cta: 'Explore courses',
} as const

export const coursesCatalogFinalCta = {
  title: 'Start Building Your Research Skills Today',
  lead: 'Choose the course that matches your current stage — or accelerate your progress with the complete bundle.',
  primary: 'Explore courses',
  secondary: 'Research Mastery Bundle',
} as const
