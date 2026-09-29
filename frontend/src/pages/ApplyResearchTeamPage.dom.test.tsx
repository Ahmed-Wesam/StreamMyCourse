/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getMyResearchTeam = vi.fn()
const submitResearchTeamApplication = vi.fn()
const fetchMe = vi.fn()

vi.mock('../lib/api/research-team', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/research-team')>()
  return {
    ...mod,
    getMyResearchTeam: (...args: unknown[]) => getMyResearchTeam(...args),
    submitResearchTeamApplication: (...args: unknown[]) => submitResearchTeamApplication(...args),
  }
})

vi.mock('../lib/api/session', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../lib/api/session')>()
  return {
    ...mod,
    fetchMe: (...args: unknown[]) => fetchMe(...args),
  }
})

import { ApiError } from '../lib/api/client'
import ApplyResearchTeamPage from './ApplyResearchTeamPage'

function renderApply() {
  return render(
    <MemoryRouter>
      <ApplyResearchTeamPage />
    </MemoryRouter>,
  )
}

async function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/^Full name$/i), { target: { value: 'Ada Lovelace' } })
  fireEvent.change(screen.getByLabelText(/^Country$/i), { target: { value: 'United Kingdom' } })
  fireEvent.change(screen.getByLabelText(/^Institution$/i), {
    target: { value: 'Analytical Engines' },
  })
  fireEvent.change(screen.getByLabelText(/^Position$/i), { target: { value: 'Researcher' } })
  fireEvent.change(screen.getByLabelText(/^Publication count$/i), { target: { value: '2' } })
  fireEvent.change(screen.getByLabelText(/^Project count$/i), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText(/Statistics experience/i), {
    target: { value: 'Intermediate' },
  })
  fireEvent.change(screen.getByLabelText(/Systematic review experience/i), {
    target: { value: 'Beginner' },
  })
  fireEvent.change(screen.getByLabelText(/^Interests$/i), { target: { value: 'Meta-analysis' } })
  fireEvent.change(screen.getByLabelText(/^Motivation$/i), {
    target: { value: 'I want to publish evidence.' },
  })
  fireEvent.change(screen.getByLabelText(/Weekly hours/i), {
    target: { value: '5–10 hours/week' },
  })
  fireEvent.click(screen.getByLabelText(/I acknowledge/i))
}

describe('ApplyResearchTeamPage', () => {
  beforeEach(() => {
    getMyResearchTeam.mockReset()
    submitResearchTeamApplication.mockReset()
    fetchMe.mockReset()
    getMyResearchTeam.mockResolvedValue({
      courses: [],
      eligible: true,
      canSubmit: true,
      application: null,
    })
    fetchMe.mockResolvedValue({
      userId: 'u1',
      email: 'ada@example.com',
      role: 'student',
      cognitoSub: 'sub',
      createdAt: '',
      updatedAt: '',
      givenName: 'Ada',
      familyName: 'Lovelace',
      country: 'United Kingdom',
      profession: 'Researcher',
      institution: 'Analytical Engines',
      researchInterests: 'Meta-analysis',
    })
  })

  afterEach(() => {
    cleanup()
  })

  it('prefills full name, country, institution, interests, and position from the profile', async () => {
    renderApply()

    expect(await screen.findByDisplayValue('Ada Lovelace')).toBeTruthy()
    expect(screen.getByDisplayValue('United Kingdom')).toBeTruthy()
    expect(screen.getByDisplayValue('Analytical Engines')).toBeTruthy()
    expect(screen.getByDisplayValue('Meta-analysis')).toBeTruthy()
    expect(screen.getByDisplayValue('Researcher')).toBeTruthy()
  })

  it('disables submit until required fields and acknowledgement are set', async () => {
    renderApply()
    const submit = await screen.findByRole('button', { name: /Submit application/i })
    expect(submit).toHaveProperty('disabled', true)

    await fillRequiredFields()
    expect(submit).toHaveProperty('disabled', false)
  })

  it('submits without email and shows success', async () => {
    submitResearchTeamApplication.mockResolvedValue({
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
      researchAreas: [],
      interests: 'Meta-analysis',
      motivation: 'I want to publish evidence.',
      weeklyHours: '5–10 hours/week',
      acknowledgedAt: '2026-09-01T12:00:00Z',
    })

    renderApply()
    await screen.findByRole('button', { name: /Submit application/i })
    await fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: /Submit application/i }))

    await waitFor(() => {
      expect(submitResearchTeamApplication).toHaveBeenCalled()
    })
    const body = submitResearchTeamApplication.mock.calls[0]?.[0] as Record<string, unknown>
    expect(body).not.toHaveProperty('email')
    expect(body.acknowledgement).toBe(true)
    expect(await screen.findByText(/application (has been )?submitted/i)).toBeTruthy()
  })

  it('shows distinct copy for 403 not_eligible', async () => {
    submitResearchTeamApplication.mockRejectedValue(
      new ApiError('Not eligible', 403, 'not_eligible'),
    )
    renderApply()
    await screen.findByRole('button', { name: /Submit application/i })
    await fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: /Submit application/i }))

    expect(await screen.findByText(/not eligible/i)).toBeTruthy()
  })

  it('shows distinct copy for 409 application_open', async () => {
    submitResearchTeamApplication.mockRejectedValue(
      new ApiError('Open application', 409, 'application_open'),
    )
    renderApply()
    await screen.findByRole('button', { name: /Submit application/i })
    await fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: /Submit application/i }))

    expect(await screen.findByText(/already have an open application/i)).toBeTruthy()
  })

  it('shows distinct copy for 409 reapply_not_allowed', async () => {
    submitResearchTeamApplication.mockRejectedValue(
      new ApiError('No reapply', 409, 'reapply_not_allowed'),
    )
    renderApply()
    await screen.findByRole('button', { name: /Submit application/i })
    await fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: /Submit application/i }))

    expect(await screen.findByText(/cannot reapply/i)).toBeTruthy()
  })

  it('shows distinct copy for 409 already_accepted', async () => {
    submitResearchTeamApplication.mockRejectedValue(
      new ApiError('Already accepted', 409, 'already_accepted'),
    )
    renderApply()
    await screen.findByRole('button', { name: /Submit application/i })
    await fillRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: /Submit application/i }))

    expect(await screen.findByText(/already (been )?accepted/i)).toBeTruthy()
  })

  it('links Cancel to /research-team', async () => {
    renderApply()
    const cancel = await screen.findByRole('link', { name: /Cancel/i })
    expect(cancel.getAttribute('href')).toBe('/research-team')
  })

  it('offers weekly hours options that use an en dash', async () => {
    renderApply()
    await screen.findByLabelText(/Weekly hours/i)
    expect(screen.getByRole('option', { name: '5–10 hours/week' })).toBeTruthy()
    expect(screen.queryByRole('option', { name: '5-10 hours/week' })).toBeNull()
  })
})
