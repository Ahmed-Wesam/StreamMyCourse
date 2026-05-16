/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import InstructorDashboard from './InstructorDashboard'

const api = vi.hoisted(() => ({
  listInstructorCourses: vi.fn(),
  listLessons: vi.fn(),
  createCourse: vi.fn(),
  publishCourse: vi.fn(),
  deleteCourse: vi.fn(),
}))

const mockNavigate = vi.fn()
const mockConfirm = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('react-router-dom')
  return {
    ...mod,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    listInstructorCourses: (...args: unknown[]) => api.listInstructorCourses(...args) as ReturnType<typeof mod.listInstructorCourses>,
    listLessons: (...args: unknown[]) => api.listLessons(...args) as ReturnType<typeof mod.listLessons>,
    createCourse: (...args: unknown[]) => api.createCourse(...args) as ReturnType<typeof mod.createCourse>,
    publishCourse: (...args: unknown[]) => api.publishCourse(...args) as ReturnType<typeof mod.publishCourse>,
    deleteCourse: (...args: unknown[]) => api.deleteCourse(...args) as ReturnType<typeof mod.deleteCourse>,
  }
})

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  writable: true,
  value: mockConfirm,
})

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<InstructorDashboard />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('InstructorDashboard', () => {
  beforeEach(() => {
    api.listInstructorCourses.mockReset()
    api.listLessons.mockReset()
    api.createCourse.mockReset()
    api.publishCourse.mockReset()
    api.deleteCourse.mockReset()
    mockNavigate.mockReset()
    mockConfirm.mockReset()

    api.listInstructorCourses.mockResolvedValue([
      {
        id: 'c1',
        title: 'Python Basics',
        description: 'Learn Python',
        status: 'DRAFT',
        thumbnailUrl: 'https://example.com/thumb1.jpg',
      },
      {
        id: 'c2',
        title: 'Advanced React',
        description: 'Master React',
        status: 'PUBLISHED',
        thumbnailUrl: 'https://example.com/thumb2.jpg',
      },
    ])
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'Lesson 1',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
    ])
    api.createCourse.mockResolvedValue({ id: 'c3' })
    api.publishCourse.mockResolvedValue({ ok: true })
    api.deleteCourse.mockResolvedValue({ ok: true })
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders dashboard title', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Instructor Dashboard')).toBeTruthy()
    })
  })

  it('renders Create New Course button', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('+ Create New Course')).toBeTruthy()
    })
  })

  it('renders list of courses', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Python Basics')).toBeTruthy()
    })
    expect(screen.getByText('Advanced React')).toBeTruthy()
  })

  it('shows course status badges', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('DRAFT')).toBeTruthy()
    })
    expect(screen.getByText('PUBLISHED')).toBeTruthy()
  })

  it('shows lesson counts', async () => {
    renderDashboard()

    await waitFor(() => {
      const lessonCounts = screen.getAllByText(/lessons/i)
      expect(lessonCounts.length).toBe(2) // Two courses, each showing lesson count
    })
  })

  it('shows Manage button for each course', async () => {
    renderDashboard()

    const manageButtons = await waitFor(() => screen.getAllByText('Manage'))
    expect(manageButtons.length).toBe(2)
  })

  it('shows Publish button for draft courses', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Publish')).toBeTruthy()
    })
  })

  it('shows Delete button for each course', async () => {
    renderDashboard()

    const deleteButtons = await waitFor(() => screen.getAllByText('Delete'))
    expect(deleteButtons.length).toBe(2)
  })

  it('opens Create Course modal when button clicked', async () => {
    renderDashboard()

    const createButton = await waitFor(() => screen.getByText('+ Create New Course'))
    fireEvent.click(createButton)

    expect(screen.getByText('Create New Course')).toBeTruthy()
  })

  it('calls createCourse when form submitted', async () => {
    renderDashboard()

    const createButton = await waitFor(() => screen.getByText('+ Create New Course'))
    fireEvent.click(createButton)

    const titleInput = screen.getByPlaceholderText(/e.g., Introduction to Python/i)
    fireEvent.change(titleInput, { target: { value: 'New Course' } })

    const submitButton = screen.getByText('Create Course')
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(api.createCourse).toHaveBeenCalledWith({
        title: 'New Course',
        description: '',
      })
    })
  })

  it('calls publishCourse when Publish clicked', async () => {
    renderDashboard()

    const publishButton = await waitFor(() => screen.getByText('Publish'))
    fireEvent.click(publishButton)

    await waitFor(() => {
      expect(api.publishCourse).toHaveBeenCalledWith('c1')
    })
  })

  it('calls deleteCourse when Delete clicked and confirmed', async () => {
    mockConfirm.mockReturnValue(true)

    renderDashboard()

    const deleteButtons = await waitFor(() => screen.getAllByText('Delete'))
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(api.deleteCourse).toHaveBeenCalledWith('c1')
    })
  })

  it('does not delete when confirmation cancelled', async () => {
    mockConfirm.mockReturnValue(false)

    renderDashboard()

    const deleteButtons = await waitFor(() => screen.getAllByText('Delete'))
    fireEvent.click(deleteButtons[0])

    expect(api.deleteCourse).not.toHaveBeenCalled()
  })

  it('navigates to course management when Manage clicked', async () => {
    renderDashboard()

    const manageButtons = await waitFor(() => screen.getAllByText('Manage'))
    fireEvent.click(manageButtons[0])

    expect(mockNavigate).toHaveBeenCalledWith('/courses/c1')
  })

  it('shows loading state initially', () => {
    api.listInstructorCourses.mockImplementation(() => new Promise(() => {}))

    renderDashboard()

    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('shows error message when courses fail to load', async () => {
    api.listInstructorCourses.mockRejectedValue(new Error('Failed to load'))

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/Your courses could not be loaded/i)).toBeTruthy()
    })
  })

  it('shows empty state when no courses', async () => {
    api.listInstructorCourses.mockResolvedValue([])

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/No courses yet/i)).toBeTruthy()
    })
  })

  it('shows Create Your First Course button in empty state', async () => {
    api.listInstructorCourses.mockResolvedValue([])

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Create Your First Course')).toBeTruthy()
    })
  })

  it('closes modal when Cancel clicked', async () => {
    renderDashboard()

    const createButton = await waitFor(() => screen.getByText('+ Create New Course'))
    fireEvent.click(createButton)

    expect(screen.getByText('Create New Course')).toBeTruthy()

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    // Modal should close
    await waitFor(() => {
      expect(screen.queryByText('Create New Course')).toBeNull()
    })
  })

  it('disables Create Course button when title is empty', async () => {
    renderDashboard()

    const createButton = await waitFor(() => screen.getByText('+ Create New Course'))
    fireEvent.click(createButton)

    const submitButton = screen.getByText('Create Course')
    expect(submitButton.hasAttribute('disabled')).toBe(true)
  })
})
