import { describe, expect, it } from 'vitest'

import { hasResearchTeamProfileFields } from './student-profile-research-team'

describe('hasResearchTeamProfileFields', () => {
  it('returns false when country or profession is missing', () => {
    expect(hasResearchTeamProfileFields({ country: '', profession: 'Physician' })).toBe(false)
    expect(hasResearchTeamProfileFields({ country: 'Jordan', profession: '' })).toBe(false)
    expect(hasResearchTeamProfileFields({ country: '  ', profession: 'Physician' })).toBe(false)
  })

  it('returns true when both are set', () => {
    expect(hasResearchTeamProfileFields({ country: 'Jordan', profession: 'Physician' })).toBe(true)
  })
})
