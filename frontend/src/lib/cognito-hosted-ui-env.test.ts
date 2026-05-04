import { describe, expect, it } from 'vitest'

import { cognitoHostedUiEnvComplete } from './cognito-hosted-ui-env'

describe('cognitoHostedUiEnvComplete', () => {
  it('returns true when pool, client, and domain are non-empty after trim', () => {
    expect(
      cognitoHostedUiEnvComplete(
        'eu-west-1_abc',
        'clientid123',
        'prefix.auth.eu-west-1.amazoncognito.com',
      ),
    ).toBe(true)
  })

  it('returns true when values have outer whitespace only', () => {
    expect(
      cognitoHostedUiEnvComplete('  eu-west-1_abc ', ' client ', ' hosted.example.com\t'),
    ).toBe(true)
  })

  it('returns false when any required value is missing', () => {
    expect(cognitoHostedUiEnvComplete('', 'c', 'd')).toBe(false)
    expect(cognitoHostedUiEnvComplete('p', '', 'd')).toBe(false)
    expect(cognitoHostedUiEnvComplete('p', 'c', '')).toBe(false)
  })

  it('returns false when any value is only whitespace', () => {
    expect(cognitoHostedUiEnvComplete('   ', 'c', 'd')).toBe(false)
    expect(cognitoHostedUiEnvComplete('p', '\t', 'd')).toBe(false)
    expect(cognitoHostedUiEnvComplete('p', 'c', ' \n')).toBe(false)
  })

  it('returns false when any value is null or undefined', () => {
    expect(cognitoHostedUiEnvComplete(undefined, 'c', 'd')).toBe(false)
    expect(cognitoHostedUiEnvComplete('p', null, 'd')).toBe(false)
    expect(cognitoHostedUiEnvComplete('p', 'c', undefined)).toBe(false)
  })
})
