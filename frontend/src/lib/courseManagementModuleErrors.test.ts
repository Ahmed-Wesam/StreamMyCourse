import { describe, expect, it } from 'vitest'

import { ApiError } from './api'
import { moduleDeleteFailureMessage } from './courseManagementModuleErrors'

describe('moduleDeleteFailureMessage', () => {
  it('returns last-module copy for last_module_required code', () => {
    expect(moduleDeleteFailureMessage(new ApiError('x', 400, 'last_module_required'))).toContain('last module')
  })

  it('returns media cleanup copy for media_cleanup_unavailable code', () => {
    expect(moduleDeleteFailureMessage(new ApiError('x', 503, 'media_cleanup_unavailable'))).toContain('Media cleanup')
  })

  it('returns null for unrelated errors', () => {
    expect(moduleDeleteFailureMessage(new Error('oops'))).toBeNull()
    expect(moduleDeleteFailureMessage(new ApiError('nope', 500))).toBeNull()
  })
})
