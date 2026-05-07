/**
 * @vitest-environment jsdom
 */
import type { ReactNode } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('./TeacherRoleGate', () => ({
  TeacherRoleGate: ({ children }: { children: ReactNode }) => (
    <div data-testid="teacher-role-gate">{children}</div>
  ),
}))

import { ProtectedRoute } from './ProtectedRoute'

describe('ProtectedRoute', () => {
  afterEach(() => {
    cleanup()
  })

  it('delegates to TeacherRoleGate with children', () => {
    render(
      <ProtectedRoute>
        <span data-testid="inner">instructor shell</span>
      </ProtectedRoute>,
    )
    expect(screen.getByTestId('teacher-role-gate').contains(screen.getByTestId('inner'))).toBe(true)
  })
})
