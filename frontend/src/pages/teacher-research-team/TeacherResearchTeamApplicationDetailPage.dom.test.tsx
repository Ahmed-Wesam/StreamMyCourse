/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import TeacherResearchTeamApplicationDetailPage from './TeacherResearchTeamApplicationDetailPage'

const sessionApi = vi.hoisted(() => ({
  fetchMe: vi.fn(),
}))

const researchTeamTeacherApi = vi.hoisted(() => ({
  getResearchTeamApplication: vi.fn(),
  patchResearchTeamApplicationStatus: vi.fn(),
  allowResearchTeamReapply: vi.fn(),
}))

vi.mock('../../lib/api/session', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../../lib/api/session')
  return {
    ...mod,
    fetchMe: (...args: unknown[]) => sessionApi.fetchMe(...args) as ReturnType<typeof mod.fetchMe>,
  }
})

vi.mock('../../lib/api/research-team-teacher', () => ({
  getResearchTeamApplication: (...args: unknown[]) =>
    researchTeamTeacherApi.getResearchTeamApplication(...args),
  patchResearchTeamApplicationStatus: (...args: unknown[]) =>
    researchTeamTeacherApi.patchResearchTeamApplicationStatus(...args),
  allowResearchTeamReapply: (...args: unknown[]) =>
    researchTeamTeacherApi.allowResearchTeamReapply(...args),
}))

const adminProfile = {
  userId: 'u-admin',
  email: 'admin@example.com',
  role: 'admin',
  cognitoSub: 'sub-a',
  createdAt: '',
  updatedAt: '',
}

function baseApplication(overrides: Record<string, unknown> = {}) {
  return {
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
    interests: 'Systematic reviews',
    motivation: 'I want to contribute.',
    weeklyHours: '5–10 hours/week',
    acknowledgedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function renderDetail(path = '/research-team/applications/app-1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/research-team/applications/:applicationId"
          element={<TeacherResearchTeamApplicationDetailPage />}
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TeacherResearchTeamApplicationDetailPage', () => {
  beforeEach(() => {
    sessionApi.fetchMe.mockReset()
    researchTeamTeacherApi.getResearchTeamApplication.mockReset()
    researchTeamTeacherApi.patchResearchTeamApplicationStatus.mockReset()
    researchTeamTeacherApi.allowResearchTeamReapply.mockReset()
    sessionApi.fetchMe.mockResolvedValue(adminProfile)
    researchTeamTeacherApi.getResearchTeamApplication.mockResolvedValue(baseApplication())
    researchTeamTeacherApi.patchResearchTeamApplicationStatus.mockResolvedValue(
      baseApplication({ status: 'under_review' }),
    )
    researchTeamTeacherApi.allowResearchTeamReapply.mockResolvedValue(
      baseApplication({ status: 'rejected', reapplyAllowed: true }),
    )
  })

  afterEach(() => {
    cleanup()
  })

  it('changing status calls PATCH with the new status', async () => {
    renderDetail()

    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy()
    })

    fireEvent.change(screen.getByLabelText(/status/i), { target: { value: 'under_review' } })
    fireEvent.click(screen.getByRole('button', { name: /update status|save status/i }))

    await waitFor(() => {
      expect(researchTeamTeacherApi.patchResearchTeamApplicationStatus).toHaveBeenCalledWith(
        'app-1',
        'under_review',
      )
    })
  })

  it('hides allow-reapply unless status is rejected and reapplyAllowed is false', async () => {
    researchTeamTeacherApi.getResearchTeamApplication.mockResolvedValue(
      baseApplication({ status: 'submitted', reapplyAllowed: false }),
    )
    renderDetail()

    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /allow reapply/i })).toBeNull()
  })

  it('shows allow-reapply when rejected and reapplyAllowed false and clicking calls POST', async () => {
    researchTeamTeacherApi.getResearchTeamApplication.mockResolvedValue(
      baseApplication({ status: 'rejected', reapplyAllowed: false }),
    )
    renderDetail()

    const button = await screen.findByRole('button', { name: /allow reapply/i })
    fireEvent.click(button)

    await waitFor(() => {
      expect(researchTeamTeacherApi.allowResearchTeamReapply).toHaveBeenCalledWith('app-1')
    })
  })

  it('renders motivation containing script tags as literal text', async () => {
    const xss = '<script>alert(1)</script>'
    researchTeamTeacherApi.getResearchTeamApplication.mockResolvedValue(
      baseApplication({ motivation: xss, interests: 'Plain interests' }),
    )
    renderDetail()

    await waitFor(() => {
      expect(screen.getByText(xss)).toBeTruthy()
    })
    expect(document.querySelector('script')).toBeNull()
    expect(screen.getByText('Plain interests')).toBeTruthy()
  })

  it('shows the applicant research preference labels', async () => {
    researchTeamTeacherApi.getResearchTeamApplication.mockResolvedValue(
      baseApplication({ researchInterestTags: ['surgical_research', 'meta_analysis'] }),
    )
    renderDetail()

    expect(await screen.findByText('Surgical Research')).toBeTruthy()
    expect(screen.getByText('Meta-Analysis')).toBeTruthy()
  })

  it('shows an error instead of loading forever when fetchMe fails', async () => {
    sessionApi.fetchMe.mockRejectedValue(new Error('network down'))

    renderDetail()

    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByText(/Loading application/i)).toBeNull()
    expect(screen.queryByRole('heading', { name: /admin only/i })).toBeNull()
  })
})
