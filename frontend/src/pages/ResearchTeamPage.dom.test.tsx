/**
 * @vitest-environment jsdom
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getResearchTeamRequirements = vi.fn()
const getMyResearchTeam = vi.fn()
const probeSignedIn = vi.fn()

vi.mock('../lib/api/public-research-team', () => ({
  getResearchTeamRequirements: (...args: unknown[]) => getResearchTeamRequirements(...args),
}))

vi.mock('../lib/auth-session-lazy', () => ({
  probeSignedIn: (...args: unknown[]) => probeSignedIn(...args),
}))

vi.mock('../lib/api/research-team', () => ({
  getMyResearchTeam: (...args: unknown[]) => getMyResearchTeam(...args),
}))

import ResearchTeamPage from './ResearchTeamPage'

function renderResearchTeam() {
  return render(
    <MemoryRouter>
      <ResearchTeamPage />
    </MemoryRouter>,
  )
}

describe('ResearchTeamPage', () => {
  beforeEach(() => {
    getResearchTeamRequirements.mockReset()
    getMyResearchTeam.mockReset()
    probeSignedIn.mockReset()
    probeSignedIn.mockResolvedValue(false)
    getResearchTeamRequirements.mockResolvedValue({
      courses: [
        { id: 'c1', title: 'Research Methodology' },
        { id: 'c2', title: 'Statistics & SPSS' },
      ],
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the prototype frequently asked questions heading', () => {
    renderResearchTeam()
    expect(screen.getByRole('heading', { name: 'Frequently Asked Questions' })).toBeTruthy()
  })

  it('loads requirements from the public API and shows no Apply control when logged out', async () => {
    renderResearchTeam()

    expect(
      await screen.findByRole('heading', { name: 'Research Team Applications Require Eligibility' }),
    ).toBeTruthy()
    await waitFor(() => expect(getResearchTeamRequirements).toHaveBeenCalled())
    expect(screen.queryByTestId('research-team-required-course')).toBeNull()
    expect(screen.queryAllByRole('link', { name: /^Apply To Research Team$/i })).toEqual([])
    expect(screen.queryByRole('button', { name: /^apply$|submit application/i })).toBeNull()
    expect(screen.getAllByRole('link', { name: 'Explore Courses' }).length).toBeGreaterThan(0)
  })

  it('keeps the prototype guest page when required courses are empty', async () => {
    getResearchTeamRequirements.mockResolvedValue({ courses: [] })
    renderResearchTeam()

    await waitFor(() => expect(getResearchTeamRequirements).toHaveBeenCalled())
    expect(screen.queryByText(/applications are not open yet/i)).toBeNull()
    expect(screen.queryByTestId('research-team-required-course')).toBeNull()
    expect(
      screen.getByRole('heading', { name: 'Research Team Applications Require Eligibility' }),
    ).toBeTruthy()
  })

  it('does not statically import the authenticated research-team client from the page module', () => {
    const dir = dirname(fileURLToPath(import.meta.url))
    const pageSource = readFileSync(join(dir, 'ResearchTeamPage.tsx'), 'utf8')
    expect(pageSource).not.toMatch(/from ['"][^'"]*lib\/api\/research-team['"]/)
    expect(pageSource).not.toMatch(/from ['"]aws-amplify/)

    const eligibilitySource = readFileSync(
      join(dir, 'research-team', 'ResearchTeamEligibilitySection.tsx'),
      'utf8',
    )
    expect(eligibilitySource).not.toMatch(/from ['"][^'"]*lib\/api\/research-team['"]/)
  })

  it('shows certificate progress and an Apply link when signed in with canSubmit', async () => {
    probeSignedIn.mockResolvedValue(true)
    getMyResearchTeam.mockResolvedValue({
      courses: [
        { courseId: 'c1', title: 'Research Methodology', certified: true },
        { courseId: 'c2', title: 'Statistics & SPSS', certified: true },
        { courseId: 'c3', title: 'Scientific Writing', certified: false },
        { courseId: 'c4', title: 'Systematic Reviews & Meta-Analysis', certified: false },
      ],
      eligible: true,
      canSubmit: true,
      application: null,
    })

    renderResearchTeam()

    expect(await screen.findByText(/2 of 4 certificates/i)).toBeTruthy()
    const required = await screen.findAllByTestId('research-team-required-course')
    expect(required.map((el) => el.textContent)).toEqual(
      expect.arrayContaining([
        'Research Methodology',
        'Statistics & SPSS',
        'Scientific Writing',
        'Systematic Reviews & Meta-Analysis',
      ]),
    )
    const applyLinks = await screen.findAllByRole('link', { name: /^Apply To Research Team$/i })
    expect(applyLinks.length).toBeGreaterThan(0)
    for (const link of applyLinks) {
      expect(link.getAttribute('href')).toBe('/research-team/apply')
    }
  })

  it('shows applications-not-open copy when signed in with zero required courses', async () => {
    probeSignedIn.mockResolvedValue(true)
    getMyResearchTeam.mockResolvedValue({
      courses: [],
      eligible: false,
      canSubmit: false,
      application: null,
    })

    renderResearchTeam()

    expect(await screen.findByText(/Applications are not open yet/i)).toBeTruthy()
    expect(screen.queryByText(/0 of 0 certificates/i)).toBeNull()
    expect(screen.queryAllByRole('link', { name: /^Apply To Research Team$/i })).toEqual([])
  })

  it('shows unlock guidance when reapply is allowed but canSubmit is false', async () => {
    probeSignedIn.mockResolvedValue(true)
    getMyResearchTeam.mockResolvedValue({
      courses: [
        { courseId: 'c1', title: 'Research Methodology', certified: true },
        { courseId: 'c2', title: 'Statistics & SPSS', certified: false },
      ],
      eligible: false,
      canSubmit: false,
      application: {
        id: 'app-2',
        status: 'rejected',
        reapplyAllowed: true,
        submittedAt: '2026-08-01T12:00:00Z',
        fullName: 'Ada',
        email: 'ada@example.com',
        country: 'Jordan',
        institution: 'U',
        position: 'Student',
        publicationCount: 0,
        projectCount: 0,
        statsExperience: 'None',
        sysReviewExperience: 'None',
        researchAreas: [],
        interests: 'x',
        motivation: 'y',
        weeklyHours: 'Less than 5 hours/week',
        acknowledgedAt: '2026-08-01T12:00:00Z',
      },
    })

    renderResearchTeam()

    expect(await screen.findByText(/was rejected/i)).toBeTruthy()
    expect(screen.queryByText(/may apply again/i)).toBeNull()
    expect(screen.getByText(/Complete the required certificates/i)).toBeTruthy()
    expect(screen.queryAllByRole('link', { name: /^Apply To Research Team$/i })).toEqual([])
  })

  it('does not tell eligible rejected students to complete certificates while waiting on reapply', async () => {
    probeSignedIn.mockResolvedValue(true)
    getMyResearchTeam.mockResolvedValue({
      courses: [
        { courseId: 'c1', title: 'Research Methodology', certified: true },
        { courseId: 'c2', title: 'Statistics & SPSS', certified: true },
      ],
      eligible: true,
      canSubmit: false,
      application: {
        id: 'app-2',
        status: 'rejected',
        reapplyAllowed: false,
        submittedAt: '2026-08-01T12:00:00Z',
        fullName: 'Ada',
        email: 'ada@example.com',
        country: 'Jordan',
        institution: 'U',
        position: 'Student',
        publicationCount: 0,
        projectCount: 0,
        statsExperience: 'None',
        sysReviewExperience: 'None',
        researchAreas: [],
        interests: 'x',
        motivation: 'y',
        weeklyHours: 'Less than 5 hours/week',
        acknowledgedAt: '2026-08-01T12:00:00Z',
      },
    })

    renderResearchTeam()

    expect(await screen.findByText(/was rejected/i)).toBeTruthy()
    expect(screen.queryByText(/Complete the required certificates/i)).toBeNull()
    expect(screen.queryByText(/may apply again/i)).toBeNull()
  })

  it('hides Apply when signed in but canSubmit is false', async () => {
    probeSignedIn.mockResolvedValue(true)
    getMyResearchTeam.mockResolvedValue({
      courses: [
        { courseId: 'c1', title: 'Research Methodology', certified: true },
        { courseId: 'c2', title: 'Statistics & SPSS', certified: false },
      ],
      eligible: false,
      canSubmit: false,
      application: null,
    })

    renderResearchTeam()

    expect(await screen.findByText(/1 of 2 certificates/i)).toBeTruthy()
    expect(screen.queryAllByRole('link', { name: /^Apply To Research Team$/i })).toEqual([])
  })

  it('shows application status text after a prior submit', async () => {
    probeSignedIn.mockResolvedValue(true)
    getMyResearchTeam.mockResolvedValue({
      courses: [{ courseId: 'c1', title: 'Research Methodology', certified: true }],
      eligible: true,
      canSubmit: false,
      application: {
        id: 'app-1',
        status: 'under_review',
        reapplyAllowed: false,
        submittedAt: '2026-09-01T12:00:00Z',
        fullName: 'Ada',
        email: 'ada@example.com',
        country: 'Jordan',
        institution: 'U',
        position: 'Student',
        publicationCount: 0,
        projectCount: 0,
        statsExperience: 'None',
        sysReviewExperience: 'None',
        researchAreas: [],
        interests: 'x',
        motivation: 'y',
        weeklyHours: 'Less than 5 hours/week',
        acknowledgedAt: '2026-09-01T12:00:00Z',
      },
    })

    renderResearchTeam()

    expect(await screen.findByText(/under review/i)).toBeTruthy()
    expect(screen.queryAllByRole('link', { name: /^Apply To Research Team$/i })).toEqual([])
  })

  it('mentions reapply when rejected with reapplyAllowed and shows Apply only if canSubmit', async () => {
    probeSignedIn.mockResolvedValue(true)
    getMyResearchTeam.mockResolvedValue({
      courses: [
        { courseId: 'c1', title: 'Research Methodology', certified: true },
        { courseId: 'c2', title: 'Statistics & SPSS', certified: true },
      ],
      eligible: true,
      canSubmit: true,
      application: {
        id: 'app-2',
        status: 'rejected',
        reapplyAllowed: true,
        submittedAt: '2026-08-01T12:00:00Z',
        fullName: 'Ada',
        email: 'ada@example.com',
        country: 'Jordan',
        institution: 'U',
        position: 'Student',
        publicationCount: 0,
        projectCount: 0,
        statsExperience: 'None',
        sysReviewExperience: 'None',
        researchAreas: [],
        interests: 'x',
        motivation: 'y',
        weeklyHours: 'Less than 5 hours/week',
        acknowledgedAt: '2026-08-01T12:00:00Z',
      },
    })

    renderResearchTeam()

    expect(await screen.findByText(/may apply again/i)).toBeTruthy()
    const applyLinks = screen.getAllByRole('link', { name: /^Apply To Research Team$/i })
    expect(applyLinks.length).toBeGreaterThan(0)
    for (const link of applyLinks) {
      expect(link.getAttribute('href')).toBe('/research-team/apply')
    }
  })

  it('keeps courses and eligibility links and does not call the authed client when logged out', async () => {
    renderResearchTeam()

    await waitFor(() => {
      expect(getResearchTeamRequirements).toHaveBeenCalled()
    })
    expect(getMyResearchTeam).not.toHaveBeenCalled()

    expect(await screen.findByRole('heading', { name: 'Frequently Asked Questions' })).toBeTruthy()
    expect(screen.getByText(/Eligibility does not guarantee acceptance/i)).toBeTruthy()
    expect(screen.getByText(/Selection considers interviews/i)).toBeTruthy()

    const coursesLinks = screen
      .getAllByRole('link')
      .filter((link) => (link.getAttribute('href') ?? '') === '/courses')
    expect(coursesLinks.length).toBeGreaterThan(0)

    const registerLinks = screen
      .getAllByRole('link')
      .filter((link) => (link.getAttribute('href') ?? '') === '/register')
    expect(registerLinks.length).toBeGreaterThan(0)
  })
})
