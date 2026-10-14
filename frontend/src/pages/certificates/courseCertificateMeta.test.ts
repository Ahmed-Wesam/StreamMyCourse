import { describe, expect, it } from 'vitest'

import {
  PATHWAY_COURSE_TITLES,
  bundlePathwayRows,
  bundleTotalHours,
  durationLine,
} from './courseCertificateMeta'

const HOURS_SUFFIX = ' · Competency-Based Assessment'

describe('durationLine', () => {
  it.each([
    ['Research Methodology', `28 Hours${HOURS_SUFFIX}`],
    ['Statistics & SPSS', `42 Hours${HOURS_SUFFIX}`],
    ['Scientific Writing', `32 Hours${HOURS_SUFFIX}`],
    ['Systematic Reviews & Meta-Analysis', `38 Hours${HOURS_SUFFIX}`],
  ] as const)('returns the pathway hours line for %s', (title, expected) => {
    expect(durationLine(title)).toBe(expected)
  })

  it('returns null for an unknown course title', () => {
    expect(durationLine('Introduction to Python')).toBeNull()
    expect(durationLine('')).toBeNull()
  })
})

describe('bundle pathway hours', () => {
  it('bundleTotalHours is 140 (sum of pathway CERT_LEARNING_HOURS)', () => {
    expect(bundleTotalHours()).toBe(140)
    expect(bundleTotalHours()).not.toBe(65)
  })

  it('bundlePathwayRows lists all four pathway courses', () => {
    const rows = bundlePathwayRows()
    expect(rows).toHaveLength(4)
    expect(rows.map((row) => row.title)).toEqual([...PATHWAY_COURSE_TITLES])
  })

  it('bundlePathwayRows hours sum to 140 and avoid placeholder values', () => {
    const rows = bundlePathwayRows()
    const hours = rows.map((row) => row.hours)
    expect(hours.reduce((sum, value) => sum + value, 0)).toBe(140)
    expect(hours).not.toEqual([15, 20, 12, 18])
    for (const row of rows) {
      expect(row.hoursLine).toBe(durationLine(row.title))
    }
  })
})
