/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMeMock = vi.hoisted(() => vi.fn())
const patchUsersMeMock = vi.hoisted(() => vi.fn())

vi.mock('../lib/api/session', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api/session')>()
  return {
    ...actual,
    fetchMe: (...args: unknown[]) => fetchMeMock(...args),
    patchUsersMe: (...args: unknown[]) => patchUsersMeMock(...args),
  }
})

import SettingsPage from './SettingsPage'

const baseProfile = {
  userId: 'user-1',
  email: 'student@example.com',
  role: 'student',
  cognitoSub: 'sub-1',
  createdAt: '2026-06-01T12:00:00.000Z',
  updatedAt: '2026-06-01T12:00:00.000Z',
  lastLoginAt: '2026-06-15T08:00:00.000Z',
  autoplayNext: true,
  autoMarkComplete: true,
  progressCelebrations: true,
  researchInterestTags: ['systematic_reviews', 'meta_analysis'],
}

describe('SettingsPage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  beforeEach(() => {
    fetchMeMock.mockReset()
    patchUsersMeMock.mockReset()
    fetchMeMock.mockResolvedValue(baseProfile)
    patchUsersMeMock.mockImplementation(async (body) => ({ ...baseProfile, ...body }))
  })

  function renderSettings() {
    return render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )
  }

  it('shows built prototype section headings and omits deferred sections', async () => {
    renderSettings()

    expect(await screen.findByRole('heading', { name: /^Settings$/i })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Learning Preferences' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'In-Platform Notifications' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Privacy' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Research Preferences' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Platform Information' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Reset Preferences' })).toBeTruthy()

    expect(screen.queryByRole('heading', { name: 'Appearance' })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Language & Region' })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Accessibility' })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Email Preferences' })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Data & Exports' })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Connected Services' })).toBeNull()
  })

  it('does not call patchUsersMe when privacy toggles change', async () => {
    renderSettings()

    const privacySwitch = await screen.findByRole('switch', {
      name: 'Show Profile to Research Team Members',
    })
    fireEvent.click(privacySwitch)

    await waitFor(() => {
      expect(privacySwitch.getAttribute('aria-checked')).toBe('false')
    })
    expect(patchUsersMeMock).not.toHaveBeenCalled()
  })

  it('calls patchUsersMe when a built learning preference toggle changes', async () => {
    renderSettings()

    const autoplay = await screen.findByRole('switch', { name: 'Autoplay Next Lecture' })
    fireEvent.click(autoplay)

    await waitFor(() => {
      expect(patchUsersMeMock).toHaveBeenCalledWith({ autoplayNext: false })
    })
  })
})
