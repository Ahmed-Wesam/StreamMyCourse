/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CourseCatalogPage from './CourseCatalogPage'

const api = vi.hoisted(() => ({
  listCourses: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    listCourses: (...args: unknown[]) => api.listCourses(...args) as ReturnType<typeof mod.listCourses>,
  }
})

function renderCatalog() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<CourseCatalogPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CourseCatalogPage', () => {
  beforeEach(() => {
    api.listCourses.mockReset()
    api.listCourses.mockResolvedValue([
      {
        id: 'c1',
        title: 'Python Basics',
        description: 'Learn Python from scratch',
        status: 'PUBLISHED',
        thumbnailUrl: 'https://example.com/thumb1.jpg',
      },
      {
        id: 'c2',
        title: 'React Fundamentals',
        description: 'Master React development',
        status: 'PUBLISHED',
        thumbnailUrl: 'https://example.com/thumb2.jpg',
      },
    ])
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders hero section with title', async () => {
    renderCatalog()

    expect(screen.getByText(/Online courses taught by working instructors/i)).toBeTruthy()
  })

  it('renders browse courses button', async () => {
    renderCatalog()

    expect(screen.getByText('Browse courses')).toBeTruthy()
  })

  it('renders Teach on Stream My Course button', async () => {
    renderCatalog()

    expect(screen.getByText(/Teach on Stream My Course/i)).toBeTruthy()
  })

  it('renders list of courses', async () => {
    renderCatalog()

    await waitFor(() => {
      expect(screen.getByText('Python Basics')).toBeTruthy()
    })
    expect(screen.getByText('React Fundamentals')).toBeTruthy()
  })

  it('shows loading skeleton while loading', () => {
    api.listCourses.mockImplementation(() => new Promise(() => {})) // Never resolves

    renderCatalog()

    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('shows error message when courses fail to load', async () => {
    api.listCourses.mockRejectedValue(new Error('Network error'))

    renderCatalog()

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeTruthy()
    })
  })

  it('shows empty state when no courses available', async () => {
    api.listCourses.mockResolvedValue([])

    renderCatalog()

    await waitFor(() => {
      expect(screen.getByText(/No courses available/i)).toBeTruthy()
    })
  })

  it('renders On-demand courses section', async () => {
    renderCatalog()

    expect(screen.getByText('On-demand courses')).toBeTruthy()
  })

  it('renders About section', async () => {
    renderCatalog()

    expect(screen.getByText('About')).toBeTruthy()
  })

  it('renders Contact section', async () => {
    renderCatalog()

    expect(screen.getByText('Contact')).toBeTruthy()
  })

  it('links to courses section', async () => {
    renderCatalog()

    const browseLink = screen.getByText('Browse courses')
    expect(browseLink.closest('a')?.getAttribute('href')).toBe('#courses')
  })
})
