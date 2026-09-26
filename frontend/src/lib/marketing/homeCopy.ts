/** Static homepage marketing copy (no JSX). Prototype text for RS-2 Slice C. */

const HOME_COURSES_HEADING = 'Four Courses. One Complete Research Skill Set.'

export const homeHero = {
  eyebrow: 'Research · Analyze · Publish',
  headlineBefore: 'Master Medical Research. Analyze Data. ',
  headlineHighlight: 'Publish With Confidence.',
  sub: 'Comprehensive online training in research methodology, statistics, scientific writing, and systematic reviews — designed specifically for healthcare professionals.',
  primaryCta: 'Explore Courses',
  secondaryCta: 'Learn More',
  authNote: 'Built by an active medical researcher — for healthcare professionals.',
  floatCards: [
    { label: 'SPSS Analysis', value: 'ANOVA · Regression · Chi-Square' },
    { label: 'Manuscript', value: 'Publication Ready' },
    { label: 'Certificate', value: 'Competency Verified' },
  ],
  bookLabels: ['Methodology', 'Statistics', 'Writing', 'Systematic Reviews'],
} as const

export const homeTrustItems = [
  'Beginner Friendly',
  'Practical & Applied',
  'Lifetime Access',
  'Certificate of Completion',
  'Research Team Pathway',
] as const

export const homeOutcomes = {
  kicker: 'Outcomes',
  title: "What You'll Be Able To Do",
  lead: 'Master practical research skills you can immediately apply to your own projects.',
  cards: [
    {
      title: 'Conduct Your Own Study',
      body: 'Move from a research question to a complete, well-designed study you can actually run.',
    },
    {
      title: 'Analyze Data Using SPSS',
      body: 'Clean, manage, analyze, and interpret your datasets using SPSS with confidence and methodological rigor.',
    },
    {
      title: 'Write Your Own Manuscript',
      body: 'Structure every section of a scientific paper — from introduction to discussion.',
    },
    {
      title: 'Conduct Systematic Reviews & Meta-Analyses',
      body: 'Search, screen, extract, and synthesize evidence into a publishable review.',
    },
    {
      title: 'Publish Your Research',
      body: 'Choose the right journal, submit correctly, and navigate the peer-review process.',
    },
  ],
} as const

export const homeJourney = {
  kicker: 'The Path',
  title: 'Your Research Journey Starts Here',
  lead: 'A structured learning path designed to take you from beginner to independent researcher.',
  steps: [
    { num: 'STEP 01', title: 'Research Methodology', final: false },
    { num: 'STEP 02', title: 'Statistics & SPSS', final: false },
    { num: 'STEP 03', title: 'Scientific Writing', final: false },
    { num: 'STEP 04', title: 'Systematic Reviews & Meta-Analysis', final: false },
    { num: 'GOAL', title: 'Research Team Eligibility', final: true },
  ],
} as const

export const homeCourses = {
  kicker: 'Our Courses',
  title: HOME_COURSES_HEADING,
  lead: 'Take them individually, or get everything with the Research Mastery Bundle.',
  emptyMessage: 'Courses will appear here',
  viewCourse: 'View Course',
  exploreCourses: 'Explore courses',
  retryLabel: 'Try again',
} as const

export const homeBundle = {
  bestTag: 'Best Value',
  title: 'Research Mastery Bundle',
  blurb:
    'A complete research pathway — design your study, analyze data in SPSS, write and submit your manuscript, and conduct a systematic review. Everything you need from first concept to published paper, in one program.',
  cta: 'Explore courses',
} as const

export const homeBeyond = {
  kicker: 'The Opportunity',
  title: 'Beyond The Courses',
  lead: 'Research Spectrum is more than an educational platform.',
  timeline: [
    {
      step: 'Step 01',
      title: 'Complete All Four Courses',
      body: 'Build the full research skill set across methodology, statistics, writing, and reviews.',
      peak: false,
    },
    {
      step: 'Step 02',
      title: 'Earn Certificates',
      body: 'Receive a Certificate of Completion for each course you finish.',
      peak: false,
    },
    {
      step: 'Step 03',
      title: 'Apply To The Research Team',
      body: 'Become eligible to apply for the Research Spectrum Research Team.',
      peak: false,
    },
    {
      step: 'Step 04',
      title: 'Interview & Selection Process',
      body: 'Selected applicants move through interviews and a structured review.',
      peak: false,
    },
    {
      step: 'Step 05',
      title: 'Participate In Real Research Projects',
      body: 'Contribute to genuine, ongoing research alongside the team.',
      peak: false,
    },
    {
      step: 'The Goal',
      title: 'Potential Authorship & Publications',
      body: 'Earn the opportunity for authorship on published research.',
      peak: true,
    },
  ],
  eligibilityTitle: 'How Eligibility Works',
  eligibilityItems: [
    'Students who complete all four courses become eligible to apply for the Research Spectrum Research Team.',
    'Selection is based on interviews, course performance, assignments, English proficiency, and research skills.',
  ],
  eligibilityNote: 'Eligibility does not guarantee acceptance.',
  learnMore: 'Learn more',
} as const

export const homeWhy = {
  kicker: 'The Platform',
  title: 'Why Research Spectrum',
  lead: 'Everything you need to become an independent researcher.',
  features: [
    {
      title: 'Real Research Datasets',
      body: 'Work with realistic datasets and practical examples that mirror real-world healthcare research.',
    },
    {
      title: 'SPSS Training Included',
      body: 'Learn how to clean data, select statistical tests, analyze results, and interpret SPSS output.',
    },
    {
      title: 'Certificate-Based Assessment',
      body: 'Earn certificates by successfully completing quizzes, assignments, and competency-based evaluations.',
    },
    {
      title: 'Healthcare-Focused Curriculum',
      body: 'Designed specifically for medical students, residents, researchers, and healthcare professionals.',
    },
    {
      title: 'Practical Assignments',
      body: 'Apply each concept through hands-on assignments designed to build real, usable research skills.',
    },
  ],
} as const

export const homeFaqPreview = {
  kicker: 'FAQ',
  title: 'Frequently Asked Questions',
  lead: 'Common questions from future students.',
  items: [
    {
      question: 'Do I need prior research experience?',
      answer:
        "No. The courses are designed to take learners from beginner level to independent research capability. You'll start with core concepts and progress through each skill systematically — no prior experience is assumed.",
    },
    {
      question: 'Do I need statistics knowledge before starting?',
      answer:
        'No. The Statistics & SPSS course starts with fundamental concepts before progressing to analyses including Chi-Square, ANOVA, Regression, Logistic Regression, Survival Analysis, and SPSS output interpretation. All statistical work is done inside SPSS with guided instruction.',
    },
    {
      question: 'Is SPSS included in the training?',
      answer:
        "Yes. The Statistics & SPSS course includes extensive hands-on SPSS instruction — you'll learn to enter and clean data, run the full range of statistical tests, and correctly interpret your SPSS output for inclusion in manuscripts.",
    },
    {
      question: 'How long do I have access?',
      answer:
        'You receive lifetime access to every course you purchase. There are no subscriptions, no recurring fees — pay once and return to your material for as long as the course remains available.',
    },
  ],
  viewAll: 'View All FAQs',
} as const

export const homeFinalCta = {
  title: 'Become an Independent Researcher',
  lead: 'Learn the exact skills needed to design studies, analyze data, write manuscripts, and publish research with confidence.',
  primary: 'Explore courses',
  secondary: 'Learn More',
} as const
