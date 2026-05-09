/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import LearnRedirectPage from './LearnRedirectPage'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../lib/api', () => {
  return {
    listCourses: vi.fn(async () => [{ id: 'c-1', title: 'Course 1', description: '', status: 'PUBLISHED' }]),
    listLessons: vi.fn(async () => [{ id: 'l-1', title: 'Lesson 1', order: 1, moduleId: 'm-1', moduleOrder: 1 }]),
  }
})

describe('LearnRedirectPage', () => {
  afterEach(() => {
    cleanup()
    mockNavigate.mockReset()
    vi.clearAllMocks()
  })

  it('redirects to the first lesson when courses + lessons exist', async () => {
    render(
      <MemoryRouter>
        <LearnRedirectPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/courses/c-1/lessons/l-1', { replace: true })
    })
  })

  it('shows an empty-courses message when no courses exist', async () => {
    const api = await import('../lib/api')
    vi.mocked(api.listCourses).mockResolvedValueOnce([])

    render(
      <MemoryRouter>
        <LearnRedirectPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/no courses available yet/i)).toBeTruthy()
    })
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('shows an empty-lessons message when first course has no lessons', async () => {
    const api = await import('../lib/api')
    vi.mocked(api.listLessons).mockResolvedValueOnce([])

    render(
      <MemoryRouter>
        <LearnRedirectPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/no lessons available yet/i)).toBeTruthy()
    })
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('shows an error message when API calls fail', async () => {
    const api = await import('../lib/api')
    vi.mocked(api.listCourses).mockRejectedValueOnce(new Error('Boom'))

    render(
      <MemoryRouter>
        <LearnRedirectPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/boom/i)).toBeTruthy()
    })
    expect(mockNavigate).not.toHaveBeenCalled()
  })
})

