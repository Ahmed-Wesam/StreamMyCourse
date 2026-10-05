export type CourseVisualKey = 'methodology' | 'statistics' | 'writing' | 'srma'

const TITLES: Record<string, CourseVisualKey> = {
  'research methodology': 'methodology',
  'statistics & spss': 'statistics',
  'scientific writing': 'writing',
  'systematic reviews & meta-analysis': 'srma',
}

export function courseVisualKey(title: string): CourseVisualKey | null {
  return TITLES[title.trim().toLowerCase()] ?? null
}

/** Display labels from the prototype curriculum. Not a lesson duration column. */
export const MODULE_DURATIONS: Record<CourseVisualKey, Record<string, string>> = {
  methodology: {
    'Introduction to Medical Research': '~1 hr',
    'Finding Research Ideas': '~1 hr',
    'Literature Review': '~1.5 hrs',
    'Research Questions & Hypotheses': '~1 hr',
    'Study Designs': '~2 hrs',
    'Variables & Measurements': '~1.5 hrs',
    Sampling: '~1.5 hrs',
    'Bias & Validity': '~1 hr',
    'Ethics & Approvals': '~1 hr',
    'Data Collection': '~1 hr',
    'Writing The Methodology Section': '~1 hr',
    'Protocol Development': '~1.5 hrs',
  },
  statistics: {
    'Introduction to Research Statistics & SPSS': '~1.5 hrs',
    'Data Management & Data Cleaning': '~2.5 hrs',
    'Descriptive Statistics': '~2 hrs',
    'Choosing the Correct Statistical Test': '~1.5 hrs',
    'Comparing Groups': '~3 hrs',
    'Association Analysis': '~2 hrs',
    'Regression Analysis': '~2.5 hrs',
    'Writing Methods & Results': '~2 hrs',
    'Real-World Applications': '~1.5 hrs',
    'Final Project': '~1.5 hrs',
  },
  writing: {
    'Introduction to Scientific Writing': '~0.5 hrs',
    'Understanding Manuscript Structure': '~1 hr',
    'Writing Effective Titles & Abstracts': '~1 hr',
    'Writing The Introduction': '~1 hr',
    'Writing The Methods Section': '~2 hrs',
    'Writing The Results Section': '~1 hr',
    'Writing The Discussion Section': '~1 hr',
    'References & Citation Management': '~0.5 hrs',
    'Journal Selection': '~1 hr',
    'Submission Preparation': '~1 hr',
    'Peer Review & Revisions': '~1 hr',
    'Final Manuscript Project': '~1 hr',
  },
  srma: {
    'Introduction to Evidence Synthesis': '~1 hr',
    'Research Questions': '~1.5 hrs',
    'Protocol Development': '~1.5 hrs',
    'Database Searching': '~2 hrs',
    'Study Screening': '~2 hrs',
    'Data Extraction': '~2 hrs',
    'Risk of Bias Assessment': '~1.5 hrs',
    'Introduction to Meta-Analysis': '~2 hrs',
    Interpretation: '~1 hr',
    'PRISMA Reporting': '~1 hr',
    'Writing The Review': '~1.5 hrs',
    'Final Project': '~1 hr',
  },
}

export const FEATURED_MODULES: Record<CourseVisualKey, ReadonlySet<string>> = {
  methodology: new Set(['Study Designs']),
  statistics: new Set(),
  writing: new Set(['Writing The Methods Section', 'Writing The Discussion Section']),
  srma: new Set(['Study Screening', 'Risk of Bias Assessment', 'Introduction to Meta-Analysis']),
}

export const JOURNEY: Record<CourseVisualKey, { sectionClass: string; lead: string; note: string; current: number }> = {
  methodology: {
    sectionClass: 'sec',
    lead: 'Research Methodology is the foundation of the complete Research Spectrum pathway toward independent research.',
    note: 'Research Methodology provides the foundation upon which the rest of the Research Spectrum pathway is built. Completing all four courses makes you eligible to apply to the Research Spectrum Research Team.',
    current: 0,
  },
  statistics: {
    sectionClass: 'sec',
    lead: 'This course is one component of the complete Research Spectrum pathway toward independent research.',
    note: 'Statistics is one component of the complete Research Spectrum pathway toward independent research. Complete all four courses to become eligible to apply to the Research Spectrum Research Team.',
    current: 1,
  },
  writing: {
    sectionClass: 'sec problem',
    lead: 'Scientific Writing is the stage where your completed research becomes a publishable manuscript.',
    note: 'Scientific Writing is where research becomes publication. Learn how to transform completed studies into professional manuscripts and move confidently through the publication process. Completing all four Research Spectrum courses makes you eligible to apply to the Research Spectrum Research Team.',
    current: 2,
  },
  srma: {
    sectionClass: 'sec problem',
    lead: 'Systematic Reviews & Meta-Analysis is the stage where existing evidence is synthesized into publishable conclusions.',
    note: 'Learn how to synthesize existing evidence into high-quality, publishable reviews. Completing all four courses makes you eligible to apply to the Research Spectrum Research Team.',
    current: 3,
  },
}

export const STUDY_DESIGNS = [
  { title: 'Cross-Sectional', body: 'A snapshot at a single point in time.' },
  { title: 'Case-Control', body: 'Start with outcomes and look backward.' },
  { title: 'Cohort', body: 'Follow participants over time.' },
  { title: 'Randomized Controlled Trial', body: 'Compare interventions under controlled conditions.' },
] as const

export const REJECTION_ITEMS = [
  'Weak study rationale',
  'Poorly written discussion sections',
  'Inadequate reporting of methods',
  'Journal mismatch',
  'Formatting and submission errors',
  'Failure to address reviewer comments',
] as const

/** Prototype curriculum note with no page_content key. Shown under Complete Curriculum. */
export const CURRICULUM_NOTES: Partial<Record<CourseVisualKey, { title: string; body: string }>> = {
  writing: {
    title: 'A Manuscript Is More Than Writing',
    body: 'Successful publication requires more than writing individual sections. Researchers must understand reporting standards, journal expectations, reviewer feedback, submission requirements, and scientific communication principles — this course addresses the complete publication process.',
  },
}

/**
 * Prototype problem-callout paragraphs for courses whose stored page_content
 * has calloutTitle and no calloutBody. A stored calloutBody still wins.
 */
export const PROBLEM_CALLOUT_BODY: Partial<Record<CourseVisualKey, string>> = {
  srma: 'Learn a structured framework used in publishable systematic reviews and meta-analyses — built on PRISMA, registered protocols, and the standards journals actually expect.',
}

export const REVIEW_TOOLS = [
  'PubMed',
  'Google Scholar',
  'Rayyan',
  'PRISMA Flow Diagrams',
  'Risk of Bias Tools',
  'Forest Plot Interpretation',
  'Meta-Analysis Software',
] as const

export const JOURNEY_STEPS = [
  'Research Methodology',
  'Statistics & SPSS',
  'Scientific Writing',
  'Systematic Reviews & Meta-Analysis',
  'Research Team Eligibility',
] as const
