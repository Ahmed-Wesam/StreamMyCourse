import { describe, expect, it } from 'vitest'

import { isCognitoRefreshSessionSupersededError } from './cognito-session-superseded'

describe('isCognitoRefreshSessionSupersededError', () => {
  it('matches Cognito Pre Token deny message from session_sync', () => {
    expect(
      isCognitoRefreshSessionSupersededError(
        new Error(
          'student refresh session superseded (client_metadata_session_id_vs_rds_active)',
        ),
      ),
    ).toBe(true)
  })

  it('matches UserLambdaValidationException wrapper text', () => {
    const err = new Error(
      'PreTokenGeneration failed with error student refresh session superseded (client_metadata_session_id_vs_rds_active).',
    )
    err.name = 'UserLambdaValidationException'
    expect(isCognitoRefreshSessionSupersededError(err)).toBe(true)
  })

  it('does not match generic refresh/network errors', () => {
    expect(isCognitoRefreshSessionSupersededError(new Error('refresh denied'))).toBe(false)
    expect(isCognitoRefreshSessionSupersededError(new Error('Network Error'))).toBe(false)
    expect(isCognitoRefreshSessionSupersededError(undefined)).toBe(false)
  })

  it('does not match unrelated Pre Token or UserLambdaValidation failures', () => {
    expect(
      isCognitoRefreshSessionSupersededError(
        new Error('PreTokenGeneration failed with error database timeout'),
      ),
    ).toBe(false)
    const ulv = new Error('invalid session policy')
    ulv.name = 'UserLambdaValidationException'
    expect(isCognitoRefreshSessionSupersededError(ulv)).toBe(false)
  })
})
