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
vi.mock('../pages/QuestionBanksListPage', () => ({
  default: () => <div data-testid="teacher-page-question-banks-list" />,
}))
vi.mock('../pages/QuestionBankStudioPage', () => ({
  default: () => <div data-testid="teacher-page-question-bank-studio" />,
}))
vi.mock('../pages/TeacherPaymentSetup', () => ({
  default: () => <div data-testid="teacher-page-payments" />,
}))
vi.mock('../pages/teacher-research-team/TeacherResearchTeamApplicationsPage', () => ({
  default: () => <div data-testid="teacher-page-research-team-list" />,
}))
vi.mock('../pages/teacher-research-team/TeacherResearchTeamApplicationDetailPage', () => ({
  default: () => <div data-testid="teacher-page-research-team-detail" />,
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

  it('mounts the instructor dashboard at /', async () => {
    renderAt('/')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-dashboard')).toBeTruthy()
    })
  })

  it('mounts course management at /courses/:courseId', async () => {
    renderAt('/courses/c-1')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-course-mgmt')).toBeTruthy()
    })
  })

  it('mounts the question banks list at /courses/:courseId/question-banks', async () => {
    renderAt('/courses/c-1/question-banks')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-question-banks-list')).toBeTruthy()
    })
  })

  it('mounts the question bank studio at /courses/:courseId/question-banks/:bankId', async () => {
    renderAt('/courses/c-1/question-banks/qb-1')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-question-bank-studio')).toBeTruthy()
    })
  })

  it('mounts payment setup at /settings/payments', async () => {
    renderAt('/settings/payments')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-payments')).toBeTruthy()
    })
  })

  it('mounts research team applications list at /research-team/applications', async () => {
    renderAt('/research-team/applications')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-research-team-list')).toBeTruthy()
    })
  })

  it('mounts research team application detail at /research-team/applications/:id', async () => {
    renderAt('/research-team/applications/app-1')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-research-team-detail')).toBeTruthy()
    })
  })

  it('redirects unknown paths to dashboard', async () => {
    renderAt('/unknown/segment')
    await waitFor(() => {
      expect(screen.getByTestId('teacher-page-dashboard')).toBeTruthy()
    })
  })
})
