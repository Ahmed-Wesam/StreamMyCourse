/**
 * @vitest-environment jsdom
 */
import type { ReactNode } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const isAuthConfiguredMock = vi.hoisted(() => vi.fn())

vi.mock('../../lib/auth', () => ({
  isAuthConfigured: () => isAuthConfiguredMock(),
}))

vi.mock('./SignIn', () => ({
  SignIn: ({ children }: { children?: ReactNode }) => <>{children}</>,
}))

vi.mock('../../pages/LessonPlayerPage', () => ({
  default: () => <div data-testid="lesson-player-stub" />,
}))

import { StudentLessonAuth } from './StudentLessonAuth'

describe('StudentLessonAuth', () => {
  beforeEach(() => {
    isAuthConfiguredMock.mockReset()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows a build-time message when Cognito is not configured', () => {
    isAuthConfiguredMock.mockReturnValue(false)
    render(<StudentLessonAuth />)
    expect(
      screen.getByText(/Cognito environment variables are not set for this build/i),
    ).toBeTruthy()
  })

  it('wraps the lesson player when Cognito is configured', () => {
    isAuthConfiguredMock.mockReturnValue(true)
    render(<StudentLessonAuth />)
    expect(screen.getByTestId('lesson-player-stub')).toBeTruthy()
  })
})
