/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client', () => ({
  httpGet: vi.fn(),
  httpPost: vi.fn(),
}))

import { httpGet, httpPost } from './client'
import {
  getMyResearchTeam,
  submitResearchTeamApplication,
  type ResearchTeamApplication,
  type SubmitResearchTeamApplicationBody,
} from './research-team'

const sampleApplication: ResearchTeamApplication = {
  id: 'app-1',
  status: 'submitted',
  reapplyAllowed: false,
  submittedAt: '2026-09-01T12:00:00Z',
  fullName: 'Ada Lovelace',
  email: 'ada@example.com',
  country: 'United Kingdom',
  institution: 'Analytical Engines',
  position: 'Researcher',
  publicationCount: 2,
  projectCount: 1,
  statsExperience: 'Intermediate',
  sysReviewExperience: 'Beginner',
  researchAreas: ['Clinical Research'],
  interests: 'Meta-analysis',
  motivation: 'I want to publish.',
  weeklyHours: '5–10 hours/week',
  acknowledgedAt: '2026-09-01T12:00:00Z',
}

describe('research-team authed client', () => {
  beforeEach(() => {
    vi.mocked(httpGet).mockReset()
    vi.mocked(httpPost).mockReset()
  })

  it('GETs /me/research-team and maps courses, flags, and application', async () => {
    vi.mocked(httpGet).mockResolvedValue({
      courses: [
        { courseId: 'c1', title: 'Research Methodology', certified: true },
        { courseId: 'c2', title: 'Statistics & SPSS', certified: false },
      ],
      eligible: false,
      canSubmit: false,
      application: sampleApplication,
    })

    const result = await getMyResearchTeam()

    expect(vi.mocked(httpGet).mock.calls.at(-1)?.[0]).toBe('/me/research-team')
    expect(result).toEqual({
      courses: [
        { courseId: 'c1', title: 'Research Methodology', certified: true },
        { courseId: 'c2', title: 'Statistics & SPSS', certified: false },
      ],
      eligible: false,
      canSubmit: false,
      application: sampleApplication,
    })
  })

  it('maps a null application from GET /me/research-team', async () => {
    vi.mocked(httpGet).mockResolvedValue({
      courses: [],
      eligible: true,
      canSubmit: true,
      application: null,
    })

    const result = await getMyResearchTeam()
    expect(result.application).toBeNull()
    expect(result.canSubmit).toBe(true)
  })

  it('POSTs /me/research-team/applications without an email field', async () => {
    const body: SubmitResearchTeamApplicationBody = {
      fullName: 'Ada Lovelace',
      country: 'United Kingdom',
      institution: 'Analytical Engines',
      position: 'Researcher',
      publicationCount: 2,
      projectCount: 1,
      statsExperience: 'Intermediate',
      sysReviewExperience: 'Beginner',
      interests: 'Meta-analysis',
      motivation: 'I want to publish.',
      weeklyHours: '5–10 hours/week',
      acknowledgement: true,
      researchAreas: ['Clinical Research', 'Epidemiology'],
    }
    vi.mocked(httpPost).mockResolvedValue(sampleApplication)

    const result = await submitResearchTeamApplication(body)

    expect(vi.mocked(httpPost).mock.calls.at(-1)?.[0]).toBe('/me/research-team/applications')
    const sent = vi.mocked(httpPost).mock.calls.at(-1)?.[1] as Record<string, unknown>
    expect(sent).not.toHaveProperty('email')
    expect(sent.acknowledgement).toBe(true)
    expect(sent.weeklyHours).toBe('5–10 hours/week')
    expect(result.id).toBe('app-1')
  })
})
