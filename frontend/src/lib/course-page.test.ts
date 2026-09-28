import { describe, expect, it } from 'vitest'

import {
  COURSE_PAGE_SECTION_KEYS,
  DEFAULT_SECTION_HEADINGS,
  effectiveSectionHeading,
  sectionHasText,
  type CoursePageDocument,
} from './course-page'

const emptyPage: CoursePageDocument = {}

describe('sectionHasText', () => {
  it('returns false for every section on a whitespace-only page', () => {
    const page: CoursePageDocument = {
      subtitle: '   ',
      level: '\n\t',
      catalogSkills: ['  ', ''],
      curriculumLead: '  ',
      problem: {
        heading: ' ',
        lead: '',
        items: ['   '],
        calloutTitle: ' ',
        calloutBody: '',
      },
      outcomes: { heading: ' ', lead: ' ', items: [] },
    }

    for (const key of COURSE_PAGE_SECTION_KEYS) {
      expect(sectionHasText(key, page), key).toBe(false)
    }
    expect(sectionHasText('problem', emptyPage)).toBe(false)
  })

  it('detects problem content and effectiveSectionHeading uses the default when heading is blank', () => {
    const page: CoursePageDocument = {
      problem: {
        heading: '   ',
        items: ['Not knowing which statistical test to choose'],
      },
    }

    expect(sectionHasText('problem', page)).toBe(true)
    expect(effectiveSectionHeading(page.problem, DEFAULT_SECTION_HEADINGS.problem)).toBe(
      DEFAULT_SECTION_HEADINGS.problem,
    )
  })

  it('treats comparison text with less-than as normal visible copy', () => {
    const page: CoursePageDocument = {
      outcomes: {
        lead: 'Interpret significance including p < 0.05 in your write-up.',
      },
    }

    expect(sectionHasText('outcomes', page)).toBe(true)
    expect(page.outcomes?.lead).toContain('p < 0.05')
  })
})

describe('effectiveSectionHeading', () => {
  it('returns trimmed custom heading when present', () => {
    expect(
      effectiveSectionHeading({ heading: '  Custom title  ' }, DEFAULT_SECTION_HEADINGS.outcomes),
    ).toBe('Custom title')
  })
})
