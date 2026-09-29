/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import TeacherResearchTeamApplicationsPage from './TeacherResearchTeamApplicationsPage'

const sessionApi = vi.hoisted(() => ({
  fetchMe: vi.fn(),
}))

const researchTeamTeacherApi = vi.hoisted(() => ({
  listResearchTeamApplications: vi.fn(),
}))

vi.mock('../../lib/api/session', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../../lib/api/session')
  return {
    ...mod,
    fetchMe: (...args: unknown[]) => sessionApi.fetchMe(...args) as ReturnType<typeof mod.fetchMe>,
  }
})

vi.mock('../../lib/api/research-team-teacher', () => ({
  listResearchTeamApplications: (...args: unknown[]) =>
    researchTeamTeacherApi.listResearchTeamApplications(...args),
}))

const adminProfile = {
  userId: 'u-admin',
  email: 'admin@example.com',
  role: 'admin',
  cognitoSub: 'sub-a',
  createdAt: '',
  updatedAt: '',
}

const teacherProfile = {
  userId: 'u-teacher',
  email: 'teacher@example.com',
  role: 'teacher',
  cognitoSub: 'sub-t',
  createdAt: '',
  updatedAt: '',
}

function renderList(path = '/research-team/applications') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/research-team/applications" element={<TeacherResearchTeamApplicationsPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TeacherResearchTeamApplicationsPage', () => {
  beforeEach(() => {
    sessionApi.fetchMe.mockReset()
    researchTeamTeacherApi.listResearchTeamApplications.mockReset()
    sessionApi.fetchMe.mockResolvedValue(adminProfile)
    researchTeamTeacherApi.listResearchTeamApplications.mockResolvedValue({
      applications: [
        {
          id: 'app-1',
          userSub: 'student-sub',
          status: 'submitted',
          reapplyAllowed: false,
          submittedAt: '2026-01-01T00:00:00Z',
          fullName: 'Ada Lovelace',
          email: 'ada@example.com',
          country: 'UK',
          institution: 'Cambridge',
          position: 'Analyst',
          publicationCount: 2,
          projectCount: 1,
          statsExperience: 'Beginner',
          sysReviewExperience: 'None',
          researchAreas: ['Oncology'],
          interests: 'Meta-analysis',
          motivation: 'I want to contribute.',
          weeklyHours: '5–10 hours/week',
          acknowledgedAt: '2026-01-01T00:00:00Z',
        },
      ],
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders an application fullName for admin', async () => {
    renderList()

    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy()
    })
    expect(researchTeamTeacherApi.listResearchTeamApplications).toHaveBeenCalledTimes(1)
  })

  it('shows not-allowed and does not call list API when role is teacher', async () => {
    sessionApi.fetchMe.mockResolvedValue(teacherProfile)

    renderList()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /admin only/i })).toBeTruthy()
    })
    expect(researchTeamTeacherApi.listResearchTeamApplications).not.toHaveBeenCalled()
  })

  it('shows an error instead of loading forever when fetchMe fails', async () => {
    sessionApi.fetchMe.mockRejectedValue(new Error('network down'))

    renderList()

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByText(/Loading applications/i)).toBeNull()
    expect(screen.queryByRole('heading', { name: /admin only/i })).toBeNull()
  })
})
