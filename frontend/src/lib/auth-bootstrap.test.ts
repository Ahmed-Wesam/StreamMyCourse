import { describe, expect, it } from 'vitest'

import { needsAuthBootstrap } from './auth-bootstrap'

describe('needsAuthBootstrap', () => {
  describe('public catalog routes', () => {
    it('returns false for home with empty search', () => {
      expect(needsAuthBootstrap('/', '')).toBe(false)
    })

    it('returns false for course details; hash is not part of search', () => {
      expect(needsAuthBootstrap('/details', '')).toBe(false)
    })

    it('returns false for course list', () => {
      expect(needsAuthBootstrap('/courses', '')).toBe(false)
    })

    it('returns false for course detail (not lesson or quiz)', () => {
      expect(needsAuthBootstrap('/courses/c1', '')).toBe(false)
    })
  })

  describe('OAuth callback (search only; hash ignored)', () => {
    it('returns true when both trimmed non-empty code and state are present', () => {
      expect(needsAuthBootstrap('/', '?code=abc&state=xyz')).toBe(true)
    })

    it('returns false when only code is present', () => {
      expect(needsAuthBootstrap('/', '?code=only')).toBe(false)
    })

    it('returns false when only state is present', () => {
      expect(needsAuthBootstrap('/', '?state=only')).toBe(false)
    })
  })

  describe('authenticated routes', () => {
    it('returns true for login', () => {
      expect(needsAuthBootstrap('/login', '')).toBe(true)
    })

    it('returns true for account profile', () => {
      expect(needsAuthBootstrap('/account/profile', '')).toBe(true)
    })

    it('returns true for billing success', () => {
      expect(needsAuthBootstrap('/billing/success', '')).toBe(true)
    })

    it('returns true for lesson player', () => {
      expect(needsAuthBootstrap('/courses/c1/lessons/l1', '')).toBe(true)
    })

    it('returns true for module quiz', () => {
      expect(needsAuthBootstrap('/courses/c1/modules/m1/quiz', '')).toBe(true)
    })
  })
})
