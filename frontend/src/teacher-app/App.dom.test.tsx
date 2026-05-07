/**
 * @vitest-environment jsdom
 */
import type { ReactNode } from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../components/auth/SignIn', () => ({
  SignIn: ({ children }: { children?: ReactNode }) => <>{children}</>,
}))
vi.mock('../components/auth/ProtectedRoute', () => ({
  ProtectedRoute: ({ children }: { children: ReactNode }) => <>{children}</>,
}))
vi.mock('../components/auth/PostLoginRedirect', () => ({
  PostLoginRedirect: () => null,
}))
vi.mock('./TeacherHeader', () => ({
  TeacherHeader: () => null,
}))
vi.mock('../pages/InstructorDashboard', () => ({
  default: () => <div data-testid="teacher-page-dashboard" />,
}))
vi.mock('../pages/CourseManagement', () => ({
  default: () => <div data-testid="teacher-page-course-mgmt" />,
}))

import TeacherApp from './App'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <TeacherApp />
    </MemoryRouter>,
  )
}

describe('TeacherApp', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('mounts the instructor dashboard at /', () => {
    renderAt('/')
    expect(screen.getByTestId('teacher-page-dashboard')).toBeTruthy()
  })

  it('mounts course management at /courses/:courseId', () => {
    renderAt('/courses/c-1')
    expect(screen.getByTestId('teacher-page-course-mgmt')).toBeTruthy()
  })

  it('redirects unknown paths to dashboard', async () => {
    renderAt('/unknown/segment')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-dashboard')).toBeTruthy()
    })
  })
})
