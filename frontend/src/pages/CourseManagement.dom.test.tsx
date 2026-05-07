/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CourseManagement from './CourseManagement'

const api = vi.hoisted(() => ({
  getCourse: vi.fn(),
  updateCourse: vi.fn(),
  listLessons: vi.fn(),
  createLesson: vi.fn(),
  deleteLesson: vi.fn(),
  getUploadUrl: vi.fn(),
  markLessonVideoReady: vi.fn(),
  markCourseThumbnailReady: vi.fn(),
  publishCourse: vi.fn(),
}))

const mockNavigate = vi.fn()
const mockConfirm = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('react-router-dom')
  return {
    ...mod,
    useNavigate: () => mockNavigate,
    useParams: () => ({ courseId: 'c1' }),
  }
})

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    getCourse: (...args: unknown[]) => api.getCourse(...args) as ReturnType<typeof mod.getCourse>,
    updateCourse: (...args: unknown[]) => api.updateCourse(...args) as ReturnType<typeof mod.updateCourse>,
    listLessons: (...args: unknown[]) => api.listLessons(...args) as ReturnType<typeof mod.listLessons>,
    createLesson: (...args: unknown[]) => api.createLesson(...args) as ReturnType<typeof mod.createLesson>,
    deleteLesson: (...args: unknown[]) => api.deleteLesson(...args) as ReturnType<typeof mod.deleteLesson>,
    getUploadUrl: (...args: unknown[]) => api.getUploadUrl(...args) as ReturnType<typeof mod.getUploadUrl>,
    markLessonVideoReady: (...args: unknown[]) => api.markLessonVideoReady(...args) as ReturnType<typeof mod.markLessonVideoReady>,
    markCourseThumbnailReady: (...args: unknown[]) => api.markCourseThumbnailReady(...args) as ReturnType<typeof mod.markCourseThumbnailReady>,
    publishCourse: (...args: unknown[]) => api.publishCourse(...args) as ReturnType<typeof mod.publishCourse>,
  }
})

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  writable: true,
  value: mockConfirm,
})

// Mock XMLHttpRequest
class MockXMLHttpRequest {
  upload = { addEventListener: vi.fn() }
  addEventListener = vi.fn((event: string, handler: () => void) => {
    if (event === 'load') {
      setTimeout(() => handler(), 0)
    }
  })
  open = vi.fn()
  setRequestHeader = vi.fn()
  send = vi.fn()
  status = 200
  statusText = 'OK'
}

Object.defineProperty(window, 'XMLHttpRequest', {
  writable: true,
  value: MockXMLHttpRequest,
})

function renderCourseManagement() {
  return render(
    <MemoryRouter initialEntries={['/courses/c1']}>
      <Routes>
        <Route path="/courses/:courseId" element={<CourseManagement />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CourseManagement', () => {
  beforeEach(() => {
    api.getCourse.mockReset()
    api.updateCourse.mockReset()
    api.listLessons.mockReset()
    api.createLesson.mockReset()
    api.deleteLesson.mockReset()
    api.getUploadUrl.mockReset()
    api.markLessonVideoReady.mockReset()
    api.markCourseThumbnailReady.mockReset()
    api.publishCourse.mockReset()
    mockNavigate.mockReset()
    mockConfirm.mockReset()

    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'DRAFT',
    })
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
      {
        id: 'l2',
        title: 'Lesson 2',
        order: 2,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'pending',
        duration: 0,
      },
    ])
    api.updateCourse.mockResolvedValue({ ok: true })
    api.createLesson.mockResolvedValue({ lessonId: 'l3', moduleId: 'm1', order: 3 })
    api.getUploadUrl.mockResolvedValue({ uploadUrl: 'https://example.com/upload', thumbnailKey: 'thumb-key' })
    api.markLessonVideoReady.mockResolvedValue({ ok: true })
    api.markCourseThumbnailReady.mockResolvedValue({ ok: true })
    api.publishCourse.mockResolvedValue({ ok: true })
    api.deleteLesson.mockResolvedValue({ ok: true })
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders loading state initially', () => {
    api.getCourse.mockImplementation(() => new Promise(() => {}))
    api.listLessons.mockImplementation(() => new Promise(() => {}))

    renderCourseManagement()

    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('renders course not found when course is null', async () => {
    api.getCourse.mockResolvedValue(null)

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText(/Course not found/i)).toBeTruthy()
    })
  })

  it('renders course title and status', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Manage Course')).toBeTruthy()
    })
    expect(screen.getByText('DRAFT')).toBeTruthy()
  })

  it('renders list of lessons', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Lesson 1')).toBeTruthy()
    })
    expect(screen.getByText('Lesson 2')).toBeTruthy()
  })

  it('shows lesson status badges', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText(/Ready/i)).toBeTruthy()
    })
    expect(screen.getByText(/Pending/i)).toBeTruthy()
  })

  it('shows Add Lesson button for draft courses', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText(/Add Lesson/i)).toBeTruthy()
    })
  })

  it('opens Add Lesson modal when button clicked', async () => {
    renderCourseManagement()

    const addButton = await waitFor(() => screen.getByText(/Add Lesson/i))
    fireEvent.click(addButton)

    expect(screen.getByText('Add New Lesson')).toBeTruthy()
  })

  it('calls updateCourse when Save Changes clicked', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Save Changes')).toBeTruthy()
    })

    const saveButton = screen.getByText('Save Changes')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(api.updateCourse).toHaveBeenCalledWith('c1', {
        title: 'Test Course',
        description: 'Test Description',
      })
    })
  })

  it('shows Publish Course button for draft with ready lessons', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Publish Course')).toBeTruthy()
    })
  })

  it('calls publishCourse when Publish Course clicked', async () => {
    renderCourseManagement()

    const publishButton = await waitFor(() => screen.getByText('Publish Course'))
    fireEvent.click(publishButton)

    await waitFor(() => {
      expect(api.publishCourse).toHaveBeenCalledWith('c1')
    })
  })

  it('calls deleteLesson when Delete clicked and confirmed', async () => {
    mockConfirm.mockReturnValue(true)

    renderCourseManagement()

    const deleteButtons = await waitFor(() => screen.getAllByText('Delete'))
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(api.deleteLesson).toHaveBeenCalledWith('c1', 'l1')
    })
  })

  it('shows error message when API call fails', async () => {
    // Reset to return a valid course first, then make update fail
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'DRAFT',
    })
    api.updateCourse.mockRejectedValue(new Error('Failed to save'))

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Save Changes')).toBeTruthy()
    })

    const saveButton = screen.getByText('Save Changes')
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/Failed to save/i)).toBeTruthy()
    })
  })

  it('navigates back to dashboard when Back button clicked', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText(/Back to Dashboard/i)).toBeTruthy()
    })

    // The back button should navigate to '/'
    const backButton = screen.getByText(/Back to Dashboard/i)
    expect(backButton).toBeTruthy()
  })

  it('shows no lessons message when lessons array is empty', async () => {
    api.listLessons.mockResolvedValue([])

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText(/No lessons yet/i)).toBeTruthy()
    })
  })

  it('hides Add Lesson button for published courses', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
    })

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('PUBLISHED')).toBeTruthy()
    })

    expect(screen.queryByText('+ Add Lesson')).toBeNull()
  })

  it('hides Delete buttons for published courses', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
    })

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('PUBLISHED')).toBeTruthy()
    })

    expect(screen.queryByText('Delete')).toBeNull()
  })
})
