import { describe, expect, it } from 'vitest'

import { parseKinescopeTimePayload } from './kinescopePlayback'

describe('parseKinescopeTimePayload', () => {
  it('floors currentTime and duration from player payloads', () => {
    expect(parseKinescopeTimePayload({ currentTime: 12.8, duration: 400.2 })).toEqual({
      positionSec: 12,
      durationSec: 400,
    })
  })

  it('returns zeroes for missing fields', () => {
    expect(parseKinescopeTimePayload({})).toEqual({ positionSec: 0, durationSec: 0 })
  })
})
