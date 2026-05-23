/**
 * @vitest-environment jsdom
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { ReactNode } from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Outlet } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const AuthShellMock = vi.hoisted(() =>
  vi.fn(({ children }: { children?: ReactNode }) => (
    <div data-testid="auth-shell">{children}</div>
  )),
)

vi.mock('../components/auth/AuthShell', () => ({
  default: AuthShellMock,
}))

vi.mock('../pages/HomePage', () => ({
  default: () => <div data-testid="student-page-home" />,
}))
vi.mock('../pages/CoursePage', () => ({
  default: () => <div data-testid="student-page-course" />,
}))
vi.mock('../pages/CourseDetailPage', () => ({
  default: () => <div data-testid="student-page-detail" />,
}))
vi.mock('../pages/LearnRedirectPage', () => ({
  default: () => <div data-testid="student-page-learn" />,
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
vi.mock('../components/auth/StudentModuleQuizAuth', () => ({
  StudentModuleQuizAuth: () => <div data-testid="student-page-quiz" />,
}))
vi.mock('../pages/BillingSuccessPage', () => ({
  default: () => <div data-testid="student-page-billing-success" />,
}))
vi.mock('../pages/BillingCancelPage', () => ({
  default: () => <div data-testid="student-page-billing-cancel" />,
}))
vi.mock('../pages/account/AccountProfilePage', () => ({
  default: () => <div data-testid="student-page-account-profile" />,
}))
vi.mock('../pages/account/AccountSubscriptionPage', () => ({
  default: () => <div data-testid="student-page-account-subscription" />,
}))
vi.mock('../components/auth/StudentAccountAuth', () => ({
  StudentAccountAuth: () => <Outlet />,
}))
vi.mock('../components/auth/SignIn', () => ({
  SignIn: ({ children }: { children?: ReactNode }) => <>{children}</>,
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

const registerStudentSessionRefreshMetadataMock = vi.hoisted(() => vi.fn())
const hubListenMock = vi.hoisted(() => vi.fn().mockReturnValue(() => {}))

vi.mock('../lib/student-session-refresh', () => ({
  registerStudentSessionRefreshMetadata: registerStudentSessionRefreshMetadataMock,
}))

vi.mock('../lib/auth-session-lazy', () => ({
  lazySignOut: vi.fn(),
  probeSignedIn: vi.fn(),
  warmUserProfileOnce: vi.fn(),
  resetProfileWarmState: vi.fn(),
  markUserProfileWarmed: vi.fn(),
}))

vi.mock('aws-amplify/utils', () => ({
  Hub: { listen: hubListenMock },
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
    AuthShellMock.mockClear()
    vi.clearAllMocks()
  })

  it('mounts the home route at /', () => {
    renderAt('/')
    expect(screen.getByTestId('student-page-home')).toBeTruthy()
  })

  it('mounts StudentSessionGuard and registers refresh metadata at /', () => {
    registerStudentSessionRefreshMetadataMock.mockClear()
    hubListenMock.mockClear()
    renderAt('/')
    expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)
    expect(hubListenMock).toHaveBeenCalledWith('auth', expect.any(Function))
  })

  it('mounts the course detail route at /courses/:courseId', async () => {
    renderAt('/courses/c-1')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-detail')).toBeTruthy()
    })
  })

  it('mounts the course page at /details', async () => {
    renderAt('/details')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-course')).toBeTruthy()
    })
  })

  it('mounts the learn redirect at /learn', async () => {
    renderAt('/learn')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-learn')).toBeTruthy()
    })
  })

  it('mounts the courses list route at /courses', async () => {
    renderAt('/courses')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-my-course')).toBeTruthy()
    })
  })

  it('redirects /catalog to the courses list', async () => {
    renderAt('/catalog')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-my-course')).toBeTruthy()
    })
  })

  it('redirects /my-course to the courses list', async () => {
    renderAt('/my-course')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-my-course')).toBeTruthy()
    })
  })

  it('mounts the login route at /login', async () => {
    renderAt('/login')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-login')).toBeTruthy()
    })
  })

  it('mounts lesson auth at /courses/:courseId/lessons/:lessonId', async () => {
    renderAt('/courses/c-1/lessons/l-1')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-lesson')).toBeTruthy()
    })
  })

  it('mounts module quiz auth at /courses/:courseId/modules/:moduleId/quiz', async () => {
    renderAt('/courses/c-1/modules/m-1/quiz')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-quiz')).toBeTruthy()
    })
  })

  it('mounts billing success at /billing/success', async () => {
    renderAt('/billing/success')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-billing-success')).toBeTruthy()
    })
  })

  it('mounts account profile at /account/profile', async () => {
    renderAt('/account/profile')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-account-profile')).toBeTruthy()
    })
  })

  it('redirects unknown paths to home', async () => {
    renderAt('/no-such-route')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-home')).toBeTruthy()
    })
  })

  describe('AuthGate integration', () => {
    it('does not render AuthShell on the public home route /', () => {
      renderAt('/')
      expect(screen.getByTestId('student-page-home')).toBeTruthy()
      expect(AuthShellMock).not.toHaveBeenCalled()
      expect(screen.queryByTestId('auth-shell')).toBeNull()
    })

    it('loads AuthShell at /login before login route content', async () => {
      renderAt('/login')

      await waitFor(() => {
        expect(screen.getByTestId('auth-shell')).toBeTruthy()
      })
      expect(AuthShellMock).toHaveBeenCalled()

      await waitFor(() => {
        expect(screen.getByTestId('student-page-login')).toBeTruthy()
      })
    })

    it('does not import PostLoginRedirect in App.tsx (only via AuthShell)', () => {
      const appPath = join(dirname(fileURLToPath(import.meta.url)), 'App.tsx')
      const source = readFileSync(appPath, 'utf8')
      expect(source).not.toMatch(/PostLoginRedirect/)
    })
  })
})
