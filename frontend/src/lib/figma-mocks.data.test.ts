import { describe, expect, it } from 'vitest'

import { FIGMA_MOCK_COURSE_PRICING_PLANS } from './figma-mocks.data'

describe('figma-mocks.data', () => {
  it('exports non-empty pricing plans', () => {
    expect(FIGMA_MOCK_COURSE_PRICING_PLANS.length).toBeGreaterThan(0)
  })

  it('does not export instructor image src (assets module only)', async () => {
    const dataModule = await import('./figma-mocks.data')
    expect(dataModule).not.toHaveProperty('FIGMA_MOCK_COURSE_INSTRUCTOR_IMAGE_SRC')
  })
})
