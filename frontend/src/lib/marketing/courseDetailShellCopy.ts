/** RS-7 placeholder shells — generic one-liners until rich course fields ship. */
export const courseDetailShellSections = [
  {
    id: 'outcomes',
    kicker: 'Outcomes',
    title: 'What you will learn',
    lead: 'Learning outcomes for this course will be listed here.',
  },
  {
    id: 'audience',
    kicker: 'Audience',
    title: 'Who this course is for',
    lead: 'Audience details for this course will appear here.',
  },
  {
    id: 'inside',
    kicker: 'Inside the course',
    title: 'What is inside',
    lead: 'A summary of modules and materials will appear here.',
  },
  {
    id: 'faq',
    kicker: 'FAQ',
    title: 'Common questions',
    lead: 'Course-specific questions and answers will appear here.',
  },
] as const

export const courseDetailLifetimePill = 'Lifetime access'

export const courseDetailSignInPrompt =
  'Sign in to watch lessons and track your progress on this course.'

export const courseDetailNoAccessPrompt =
  'You do not have access to this course yet. Lesson playback and progress tracking require access.'
