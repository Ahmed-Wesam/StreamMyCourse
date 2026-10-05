import { describe, expect, it } from 'vitest'

import { profileInitials } from './profileInitials'

describe('profileInitials', () => {
  it('uses given and family names when present', () => {
    expect(profileInitials({ givenName: 'Ada', familyName: 'Lovelace' })).toBe('AL')
  })

  it('falls back to email local part when names are missing', () => {
    expect(profileInitials({ email: 'ahmadwesamo1@gmail.com' })).toBe('AH')
  })

  it('returns ? when nothing usable is provided', () => {
    expect(profileInitials({})).toBe('?')
  })
})
