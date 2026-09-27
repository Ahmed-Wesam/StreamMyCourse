/**
 * @vitest-environment jsdom
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { ReactNode } from 'react'
import { cleanup, configure, render, screen, waitFor } from '@testing-library/react'

configure({ asyncUtilTimeout: 5000 })
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
vi.mock('../pages/AboutInstructorPage', () => ({
  default: () => <div data-testid="student-page-about" />,
}))
vi.mock('../pages/FaqPage', () => ({
  default: () => <div data-testid="student-page-faq" />,
}))
vi.mock('../pages/ContactPage', () => ({
  default: () => <div data-testid="student-page-contact" />,
}))
vi.mock('../pages/ResearchTeamPage', () => ({
  default: () => <div data-testid="student-page-research-team" />,
}))
vi.mock('../pages/CourseDetailPage', () => ({
  default: () => <div data-testid="student-page-detail" />,
}))
vi.mock('../pages/LearnRedirectPage', () => ({
  default: () => <div data-testid="student-page-learn" />,
}))
vi.mock('../pages/CoursesCatalogPage', () => ({
  default: () => <div data-testid="student-page-catalog" />,
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
vi.mock('../pages/account/AccountPurchasesPage', () => ({
  default: () => <div data-testid="student-page-account-purchases" />,
}))
vi.mock('../pages/CheckoutPage', () => ({
  default: () => <div data-testid="student-page-checkout" />,
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

  it('mounts the home route at /', async () => {
    renderAt('/')
    expect(await screen.findByTestId('student-page-home')).toBeTruthy()
  })

  it('mounts StudentSessionGuard and registers refresh metadata at /', async () => {
    registerStudentSessionRefreshMetadataMock.mockClear()
    hubListenMock.mockClear()
    renderAt('/')
    await waitFor(() => {
      expect(registerStudentSessionRefreshMetadataMock).toHaveBeenCalledTimes(1)
    })
    expect(hubListenMock).toHaveBeenCalledWith('auth', expect.any(Function))
  })

  it('mounts the course detail route at /courses/:courseId', async () => {
    renderAt('/courses/c-1')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-detail')).toBeTruthy()
    })
  })

  it('redirects /details to the courses catalog', async () => {
    renderAt('/details')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-catalog')).toBeTruthy()
    })
    expect(screen.queryByTestId('student-page-course')).toBeNull()
  })

  it('redirects /course to the courses catalog', async () => {
    renderAt('/course')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-catalog')).toBeTruthy()
    })
    expect(screen.queryByTestId('student-page-course')).toBeNull()
  })

  it('mounts the learn redirect at /learn', async () => {
    renderAt('/learn')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-learn')).toBeTruthy()
    })
  })

  it('mounts the courses catalog at /courses without AuthShell', async () => {
    renderAt('/courses')
    expect(await screen.findByTestId('student-page-catalog')).toBeTruthy()
    expect(screen.queryByTestId('student-page-my-course')).toBeNull()
    expect(AuthShellMock).not.toHaveBeenCalled()
    expect(screen.queryByTestId('auth-shell')).toBeNull()
  })

  it('redirects /catalog to the courses catalog', async () => {
    renderAt('/catalog')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-catalog')).toBeTruthy()
    })
  })

  it('redirects /my-course to the courses catalog', async () => {
    renderAt('/my-course')
    await waitFor(() => {
      expect(screen.getByTestId('student-page-catalog')).toBeTruthy()
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

  it('mounts the about route at /about without AuthShell', async () => {
    renderAt('/about')
    expect(await screen.findByTestId('student-page-about')).toBeTruthy()
    expect(AuthShellMock).not.toHaveBeenCalled()
    expect(screen.queryByTestId('auth-shell')).toBeNull()
  })

  it('mounts the faq route at /faq without AuthShell', async () => {
    renderAt('/faq')
    expect(await screen.findByTestId('student-page-faq')).toBeTruthy()
    expect(AuthShellMock).not.toHaveBeenCalled()
    expect(screen.queryByTestId('auth-shell')).toBeNull()
  })

  it('mounts the contact route at /contact without AuthShell', async () => {
    renderAt('/contact')
    expect(await screen.findByTestId('student-page-contact')).toBeTruthy()
    expect(AuthShellMock).not.toHaveBeenCalled()
    expect(screen.queryByTestId('auth-shell')).toBeNull()
  })

  it('mounts the research-team route at /research-team without AuthShell', async () => {
    renderAt('/research-team')
    expect(await screen.findByTestId('student-page-research-team')).toBeTruthy()
    expect(AuthShellMock).not.toHaveBeenCalled()
    expect(screen.queryByTestId('auth-shell')).toBeNull()
  })

  it('keeps /register on the catch-all to home', async () => {
    renderAt('/register')
    expect(await screen.findByTestId('student-page-home')).toBeTruthy()
  })

  it('keeps /dashboard on the catch-all to home', async () => {
    renderAt('/dashboard')
    expect(await screen.findByTestId('student-page-home')).toBeTruthy()
  })

  it('keeps /certificates on the catch-all to home', async () => {
    renderAt('/certificates')
    expect(await screen.findByTestId('student-page-home')).toBeTruthy()
  })

  describe('AuthGate integration', () => {
    it('does not render AuthShell on the public home route /', async () => {
      renderAt('/')
      expect(await screen.findByTestId('student-page-home')).toBeTruthy()
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
