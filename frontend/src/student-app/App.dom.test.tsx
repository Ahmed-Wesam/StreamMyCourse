/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../pages/CourseCatalogPage', () => ({
  default: () => <div data-testid="student-page-catalog" />,
}))
vi.mock('../pages/HomePage', () => ({
  default: () => <div data-testid="student-page-home" />,
}))
vi.mock('../pages/CourseDetailPage', () => ({
  default: () => <div data-testid="student-page-detail" />,
}))
vi.mock('../pages/MyCoursePage', () => ({
  default: () => <div data-testid="student-page-my-course" />,
}))
vi.mock('../pages/StudentLoginPage', () => ({
  default: () => <div data-testid="student-page-login" />,
}))
vi.mock('../components/auth/StudentLessonAuth', () => ({
  StudentLessonAuth: () => <div data-testid="student-page-lesson" />,
}))
vi.mock('../components/auth/PostLoginRedirect', () => ({
  PostLoginRedirect: () => null,
}))
vi.mock('../components/auth/StudentProfileBootstrap', () => ({
  StudentProfileBootstrap: () => null,
}))
vi.mock('./StudentHeader', () => ({
  StudentHeader: () => null,
}))

import StudentApp from './App'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <StudentApp />
    </MemoryRouter>,
  )
}

describe('StudentApp', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('mounts the home route at /', () => {
    renderAt('/')
    expect(screen.getByTestId('student-page-home')).toBeTruthy()
  })

  it('mounts the catalog route at /catalog', () => {
    renderAt('/catalog')
    expect(screen.getByTestId('student-page-catalog')).toBeTruthy()
  })

  it('mounts the course detail route at /courses/:courseId', () => {
    renderAt('/courses/c-1')
    expect(screen.getByTestId('student-page-detail')).toBeTruthy()
  })

  it('mounts the my course route at /my-course', () => {
    renderAt('/my-course')
    expect(screen.getByTestId('student-page-my-course')).toBeTruthy()
  })

  it('mounts the login route at /login', () => {
    renderAt('/login')
    expect(screen.getByTestId('student-page-login')).toBeTruthy()
  })

  it('mounts lesson auth at /courses/:courseId/lessons/:lessonId', () => {
    renderAt('/courses/c-1/lessons/l-1')
    expect(screen.getByTestId('student-page-lesson')).toBeTruthy()
  })

  it('redirects unknown paths to home', async () => {
    renderAt('/no-such-route')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-home')).toBeTruthy()
    })
  })
})
