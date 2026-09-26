import { describe, expect, it } from 'vitest'

import { isStudentIdleProbePath, needsAuthBootstrap } from './auth-bootstrap'

describe('isStudentIdleProbePath', () => {
  it('returns true for current public catalog paths', () => {
    expect(isStudentIdleProbePath('/')).toBe(true)
    expect(isStudentIdleProbePath('/details')).toBe(true)
    expect(isStudentIdleProbePath('/learn')).toBe(true)
    expect(isStudentIdleProbePath('/courses')).toBe(true)
    expect(isStudentIdleProbePath('/courses/c1')).toBe(true)
  })

  it('returns true for marketing pages', () => {
    expect(isStudentIdleProbePath('/about')).toBe(true)
    expect(isStudentIdleProbePath('/faq')).toBe(true)
    expect(isStudentIdleProbePath('/contact')).toBe(true)
    expect(isStudentIdleProbePath('/research-team')).toBe(true)
  })

  it('returns true for legal policy paths', () => {
    expect(isStudentIdleProbePath('/privacy')).toBe(true)
    expect(isStudentIdleProbePath('/terms')).toBe(true)
    expect(isStudentIdleProbePath('/refund')).toBe(true)
    expect(isStudentIdleProbePath('/delivery')).toBe(true)
    expect(isStudentIdleProbePath('/educational-disclaimer')).toBe(true)
  })

  it('returns false for auth, account, lesson, and quiz paths', () => {
    expect(isStudentIdleProbePath('/login')).toBe(false)
    expect(isStudentIdleProbePath('/account/profile')).toBe(false)
    expect(isStudentIdleProbePath('/courses/c1/lessons/l1')).toBe(false)
    expect(isStudentIdleProbePath('/courses/c1/modules/m1/quiz')).toBe(false)
  })
})

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

    it('returns false for terms page', () => {
      expect(needsAuthBootstrap('/terms', '')).toBe(false)
    })

    it('returns false for privacy page', () => {
      expect(needsAuthBootstrap('/privacy', '')).toBe(false)
    })

    it('returns false for other legal policy pages', () => {
      expect(needsAuthBootstrap('/refund', '')).toBe(false)
      expect(needsAuthBootstrap('/delivery', '')).toBe(false)
      expect(needsAuthBootstrap('/educational-disclaimer', '')).toBe(false)
    })

    // Lock: unknown paths already return false today. Explicit branches keep a future
    // default-true change from swallowing these marketing routes.
    it('returns false for marketing pages (explicit lock, not the route red signal)', () => {
      expect(needsAuthBootstrap('/about', '')).toBe(false)
      expect(needsAuthBootstrap('/faq', '')).toBe(false)
      expect(needsAuthBootstrap('/contact', '')).toBe(false)
      expect(needsAuthBootstrap('/research-team', '')).toBe(false)
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
