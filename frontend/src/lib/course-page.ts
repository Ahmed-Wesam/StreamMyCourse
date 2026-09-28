export type CoursePageTextCard = {
  title?: string
  body?: string
}

export type CoursePageListSection = {
  heading?: string
  lead?: string
  items?: string[]
}

export type CoursePageProblemSection = CoursePageListSection & {
  calloutTitle?: string
  calloutBody?: string
}

export type CoursePageHandsOnSection = {
  heading?: string
  lead?: string
  cards?: CoursePageTextCard[]
  closingNote?: string
}

type CoursePageHighlightsSection = {
  heading?: string
  lead?: string
  items?: string[]
  closingNote?: string
}

type CoursePageAssessmentSection = {
  heading?: string
  lead?: string
  steps?: CoursePageTextCard[]
}

type CoursePageEnrollCtaSection = {
  heading?: string
  body?: string
  extraLine?: string
}

export type CoursePageDocument = {
  subtitle?: string
  level?: string
  estimatedHours?: number
  catalogSkills?: string[]
  problem?: CoursePageProblemSection
  outcomes?: CoursePageListSection
  curriculumLead?: string
  inside?: CoursePageListSection
  handsOn?: CoursePageHandsOnSection
  highlights?: CoursePageHighlightsSection
  audience?: CoursePageListSection
  assessment?: CoursePageAssessmentSection
  enrollCta?: CoursePageEnrollCtaSection
}

export const DEFAULT_SECTION_HEADINGS = {
  problem: 'The problem',
  outcomes: 'What you will learn',
  inside: 'What is inside',
  handsOn: 'Hands-on application',
  highlights: 'Key highlights',
  audience: 'Who this course is for',
  assessment: 'Assignments & certification',
  enrollCta: 'Ready to get started?',
} as const

type CoursePageSectionKey =
  | 'subtitle'
  | 'level'
  | 'estimatedHours'
  | 'catalogSkills'
  | 'curriculumLead'
  | 'problem'
  | 'outcomes'
  | 'inside'
  | 'handsOn'
  | 'highlights'
  | 'audience'
  | 'assessment'
  | 'enrollCta'

export const COURSE_PAGE_SECTION_KEYS: readonly CoursePageSectionKey[] = [
  'subtitle',
  'level',
  'estimatedHours',
  'catalogSkills',
  'curriculumLead',
  'problem',
  'outcomes',
  'inside',
  'handsOn',
  'highlights',
  'audience',
  'assessment',
  'enrollCta',
]

function trimmed(value: string | undefined): string {
  return value?.trim() ?? ''
}

function hasText(value: string | undefined): boolean {
  return trimmed(value).length > 0
}

function listHasText(items: string[] | undefined): boolean {
  return items?.some((item) => hasText(item)) ?? false
}

function cardsHaveText(cards: CoursePageTextCard[] | undefined): boolean {
  return (
    cards?.some((card) => hasText(card.title) || hasText(card.body)) ?? false
  )
}

function listSectionHasText(section: CoursePageListSection | undefined): boolean {
  if (!section) return false
  return (
    hasText(section.heading) ||
    hasText(section.lead) ||
    listHasText(section.items)
  )
}

export function sectionHasText(
  sectionKey: CoursePageSectionKey,
  page: CoursePageDocument,
): boolean {
  switch (sectionKey) {
    case 'subtitle':
      return hasText(page.subtitle)
    case 'level':
      return hasText(page.level)
    case 'estimatedHours':
      return typeof page.estimatedHours === 'number' && page.estimatedHours > 0
    case 'catalogSkills':
      return listHasText(page.catalogSkills)
    case 'curriculumLead':
      return hasText(page.curriculumLead)
    case 'problem': {
      const section = page.problem
      if (!section) return false
      return (
        listSectionHasText(section) ||
        hasText(section.calloutTitle) ||
        hasText(section.calloutBody)
      )
    }
    case 'outcomes':
      return listSectionHasText(page.outcomes)
    case 'inside':
      return listSectionHasText(page.inside)
    case 'handsOn': {
      const section = page.handsOn
      if (!section) return false
      return (
        hasText(section.heading) ||
        hasText(section.lead) ||
        cardsHaveText(section.cards) ||
        hasText(section.closingNote)
      )
    }
    case 'highlights': {
      const section = page.highlights
      if (!section) return false
      return (
        hasText(section.heading) ||
        hasText(section.lead) ||
        listHasText(section.items) ||
        hasText(section.closingNote)
      )
    }
    case 'audience':
      return listSectionHasText(page.audience)
    case 'assessment': {
      const section = page.assessment
      if (!section) return false
      return (
        hasText(section.heading) ||
        hasText(section.lead) ||
        cardsHaveText(section.steps)
      )
    }
    case 'enrollCta': {
      const section = page.enrollCta
      if (!section) return false
      return (
        hasText(section.heading) ||
        hasText(section.body) ||
        hasText(section.extraLine)
      )
    }
    default: {
      const _exhaustive: never = sectionKey
      return _exhaustive
    }
  }
}

export function effectiveSectionHeading(
  section: { heading?: string } | undefined,
  defaultHeading: string,
): string {
  const heading = trimmed(section?.heading)
  return heading.length > 0 ? heading : defaultHeading
}
