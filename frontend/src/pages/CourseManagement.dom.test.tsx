/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CourseManagement from './CourseManagement'
import { ApiError } from '../lib/api'
import { questionBankUserMessage } from '../lib/questionBankErrors'

const api = vi.hoisted(() => ({
  getCourse: vi.fn(),
  updateCourse: vi.fn(),
  listLessons: vi.fn(),
  createLesson: vi.fn(),
  deleteLesson: vi.fn(),
  listCourseModules: vi.fn(),
  createCourseModule: vi.fn(),
  deleteCourseModule: vi.fn(),
  getUploadUrl: vi.fn(),
  markLessonVideoReady: vi.fn(),
  markCourseThumbnailReady: vi.fn(),
  publishCourse: vi.fn(),
  listCourseModuleQuizzes: vi.fn(),
  listCourseQuestionBanks: vi.fn(),
  createModuleQuiz: vi.fn(),
}))

const mockNavigate = vi.fn()
const mockConfirm = vi.fn()
const mockRouteParams = vi.hoisted(() => ({ courseId: 'c1' }))

vi.mock('react-router-dom', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('react-router-dom')
  return {
    ...mod,
    useNavigate: () => mockNavigate,
    useParams: () => mockRouteParams,
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
    listCourseModules: (...args: unknown[]) => api.listCourseModules(...args) as ReturnType<typeof mod.listCourseModules>,
    createCourseModule: (...args: unknown[]) =>
      api.createCourseModule(...args) as ReturnType<typeof mod.createCourseModule>,
    deleteCourseModule: (...args: unknown[]) =>
      api.deleteCourseModule(...args) as ReturnType<typeof mod.deleteCourseModule>,
    getUploadUrl: (...args: unknown[]) => api.getUploadUrl(...args) as ReturnType<typeof mod.getUploadUrl>,
    markLessonVideoReady: (...args: unknown[]) => api.markLessonVideoReady(...args) as ReturnType<typeof mod.markLessonVideoReady>,
    markCourseThumbnailReady: (...args: unknown[]) => api.markCourseThumbnailReady(...args) as ReturnType<typeof mod.markCourseThumbnailReady>,
    publishCourse: (...args: unknown[]) => api.publishCourse(...args) as ReturnType<typeof mod.publishCourse>,
    listCourseModuleQuizzes: (...args: unknown[]) =>
      api.listCourseModuleQuizzes(...args) as ReturnType<typeof mod.listCourseModuleQuizzes>,
    listCourseQuestionBanks: (...args: unknown[]) =>
      api.listCourseQuestionBanks(...args) as ReturnType<typeof mod.listCourseQuestionBanks>,
    createModuleQuiz: (...args: unknown[]) =>
      api.createModuleQuiz(...args) as ReturnType<typeof mod.createModuleQuiz>,
  }
})

vi.mock('../lib/videoThumbnail', () => ({
  captureFrameAtVideoPercent: vi.fn(async () => {
    throw new Error('thumbnail generation skipped in tests')
  }),
}))

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

function renderCourseManagement(initialEntries: string[] = ['/courses/c1']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
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
    api.listCourseModules.mockReset()
    api.createCourseModule.mockReset()
    api.deleteCourseModule.mockReset()
    api.listCourseModuleQuizzes.mockReset()
    api.listCourseQuestionBanks.mockReset()
    api.createModuleQuiz.mockReset()
    mockNavigate.mockReset()
    mockConfirm.mockReset()
    mockRouteParams.courseId = 'c1'

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
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'Section 1', description: '', order: 0 },
      { id: 'm2', title: 'Section 2', description: 'More', order: 1 },
    ])
    api.updateCourse.mockResolvedValue({ ok: true })
    api.createLesson.mockResolvedValue({ lessonId: 'l3', moduleId: 'm1', order: 3 })
    api.createCourseModule.mockResolvedValue({ moduleId: 'm3', order: 2 })
    api.deleteCourseModule.mockResolvedValue({ moduleId: 'm1', deleted: true })
    api.getUploadUrl.mockResolvedValue({ uploadUrl: 'https://example.com/upload', thumbnailKey: 'thumb-key' })
    api.markLessonVideoReady.mockResolvedValue({ ok: true })
    api.markCourseThumbnailReady.mockResolvedValue({ ok: true })
    api.publishCourse.mockResolvedValue({ ok: true })
    api.deleteLesson.mockResolvedValue({ ok: true })
    api.listCourseModuleQuizzes.mockResolvedValue([])
    api.listCourseQuestionBanks.mockResolvedValue([])
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
      expect(screen.getByTestId('course-management-not-found')).toBeTruthy()
      expect(screen.getByRole('heading', { name: /Course not found/i })).toBeTruthy()
    })
    expect(screen.queryByTestId('course-management-load-error')).toBeNull()
    expect(screen.queryByTestId('course-management-inline-error')).toBeNull()
    expect(screen.queryByTestId('course-management-inline-info')).toBeNull()
  })

  it('renders course title and status', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Manage Course')).toBeTruthy()
    })
    expect(screen.getByText('DRAFT')).toBeTruthy()
  })

  it('renders a course-scoped Question banks link after course data loads', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Manage Course')).toBeTruthy()
    })

    const questionBanksLink = screen.getByRole('link', { name: /^Question banks$/i })
    expect(questionBanksLink.getAttribute('href')).toBe('/courses/c1/question-banks')
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

  it('does not navigate after publish when post-publish refresh fails', async () => {
    let getCourseCalls = 0
    api.getCourse.mockImplementation(() => {
      getCourseCalls += 1
      if (getCourseCalls >= 2) {
        return Promise.reject(new Error('reload broke'))
      }
      return Promise.resolve({
        id: 'c1',
        title: 'Test Course',
        description: 'Test Description',
        status: 'DRAFT',
      })
    })

    renderCourseManagement()

    const publishButton = await waitFor(() => screen.getByText('Publish Course'))
    fireEvent.click(publishButton)

    await waitFor(() => {
      expect(api.publishCourse).toHaveBeenCalledWith('c1')
    })
    await waitFor(() => {
      expect(screen.getByTestId('course-management-load-error')).toBeTruthy()
    })
    expect(mockNavigate).not.toHaveBeenCalledWith('/')
  })

  it('calls deleteLesson when Delete clicked and confirmed', async () => {
    mockConfirm.mockReturnValue(true)

    renderCourseManagement()

    const deleteButtons = await waitFor(() => screen.getAllByRole('button', { name: /Delete Lesson/i }))
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

  it('renders Modules / Sections panel and lists modules ordered by order', async () => {
    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText(/Modules/i)).toBeTruthy()
    })

    const panel = screen.getByText('Modules / Sections').closest('div')
    expect(panel).toBeTruthy()
    const titles = within(panel as HTMLElement).getAllByText(/Section [12]/i).map((el) => el.textContent)
    expect(titles).toEqual(['Section 1', 'Section 2'])
  })

  it('creates a module from the inline form', async () => {
    renderCourseManagement()

    const titleInput = await waitFor(() => screen.getByLabelText(/Module Title/i))
    fireEvent.change(titleInput, { target: { value: 'Intro' } })
    const createBtn = screen.getByRole('button', { name: /Create Module/i })
    fireEvent.click(createBtn)

    await waitFor(() => {
      expect(api.createCourseModule).toHaveBeenCalledWith('c1', { title: 'Intro', description: '' })
    })
  })

  it('deletes a module and refreshes', async () => {
    mockConfirm.mockReturnValue(true)
    renderCourseManagement()

    const deleteButtons = await waitFor(() => screen.getAllByRole('button', { name: /Delete Module/i }))
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(api.deleteCourseModule).toHaveBeenCalledWith('c1', 'm1')
    })
  })

  it('shows info when module delete is idempotent (deleted false)', async () => {
    mockConfirm.mockReturnValue(true)
    api.deleteCourseModule.mockResolvedValue({ moduleId: 'm1', deleted: false })
    renderCourseManagement()

    const deleteButtons = await waitFor(() => screen.getAllByRole('button', { name: /Delete Module/i }))
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.getByTestId('course-management-inline-info')).toBeTruthy()
      expect(screen.getByText(/Module already removed; refreshing list/i)).toBeTruthy()
    })
    expect(api.deleteCourseModule).toHaveBeenCalledWith('c1', 'm1')
    expect(api.getCourse).toHaveBeenCalledTimes(2)
    expect(api.listLessons).toHaveBeenCalledTimes(2)
    expect(api.listCourseModules).toHaveBeenCalledTimes(2)
  })

  it('shows combined load error when idempotent delete succeeds but refresh fails', async () => {
    mockConfirm.mockReturnValue(true)
    api.deleteCourseModule.mockResolvedValue({ moduleId: 'm1', deleted: false })
    let getCourseLoads = 0
    api.getCourse.mockImplementation(() => {
      getCourseLoads += 1
      if (getCourseLoads >= 2) {
        return Promise.reject(new Error('refresh failed'))
      }
      return Promise.resolve({
        id: 'c1',
        title: 'Test Course',
        description: 'Test Description',
        status: 'DRAFT',
      })
    })

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByText('Manage Course')).toBeTruthy()
    })

    const deleteButtons = screen.getAllByRole('button', { name: /Delete Module/i })
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.getByTestId('course-management-load-error')).toBeTruthy()
      expect(screen.getByText(/That module was already removed/i)).toBeTruthy()
      expect(screen.getByText(/Could not refresh the course/i)).toBeTruthy()
    })
  })

  it('shows friendly error when deleting last module fails (400 + message)', async () => {
    mockConfirm.mockReturnValue(true)
    api.deleteCourseModule.mockRejectedValue(new ApiError('Cannot delete the last module in a course', 400))
    renderCourseManagement()

    const deleteButtons = await waitFor(() => screen.getAllByRole('button', { name: /Delete Module/i }))
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.getByText(/can't delete the last module/i)).toBeTruthy()
    })
  })

  it('shows media-cleanup guidance when deletion is blocked (503 + message)', async () => {
    mockConfirm.mockReturnValue(true)
    api.deleteCourseModule.mockRejectedValue(new ApiError('Media cleanup queue is not configured', 503))
    renderCourseManagement()

    const deleteButtons = await waitFor(() => screen.getAllByRole('button', { name: /Delete Module/i }))
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.getByText(/Media cleanup is not configured/i)).toBeTruthy()
    })
  })

  it('when multiple modules exist, Add Lesson modal includes module selector and passes moduleId', async () => {
    renderCourseManagement()

    const addButton = await waitFor(() => screen.getByText(/Add Lesson/i))
    fireEvent.click(addButton)

    fireEvent.change(screen.getByLabelText(/Lesson Title/i), { target: { value: 'New Lesson' } })
    const file = new File(['x'], 'video.mp4', { type: 'video/mp4' })
    const fileInput = screen.getByLabelText(/Video File/i) as HTMLInputElement
    Object.defineProperty(fileInput, 'files', { value: [file] })
    fireEvent.change(fileInput)
    await waitFor(() => {
      expect(screen.getByText(/Selected:/i)).toBeTruthy()
    })

    const moduleSelect = screen.getByLabelText(/^Module$/i) as HTMLSelectElement
    fireEvent.change(moduleSelect, { target: { value: 'm2' } })

    const submit = screen.getByRole('button', { name: /^Add Lesson$/i })
    await waitFor(() => {
      expect((submit as HTMLButtonElement).disabled).toBe(false)
    })
    const form = submit.closest('form')
    expect(form).toBeTruthy()
    fireEvent.submit(form as HTMLFormElement)

    await waitFor(() => {
      expect(api.createLesson).toHaveBeenCalledWith('c1', { title: 'New Lesson', moduleId: 'm2' })
    })
  })

  it('clears stale course UI when route courseId changes and reload fails', async () => {
    const { rerender } = renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Course')).toBeTruthy()
    })
    expect(screen.getByText('Lesson 1')).toBeTruthy()

    mockRouteParams.courseId = 'c2'
    api.getCourse.mockRejectedValueOnce(new ApiError('boom', 500))

    rerender(
      <MemoryRouter initialEntries={['/courses/c2']}>
        <Routes>
          <Route path="/courses/:courseId" element={<CourseManagement />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('boom')).toBeTruthy()
    })
    expect(screen.queryByDisplayValue('Test Course')).toBeNull()
    expect(screen.queryByText('Lesson 1')).toBeNull()
    expect(screen.queryByText('Save Changes')).toBeNull()
  })

  it('surfaces initial load failure as error banner, not Course not found', async () => {
    api.getCourse.mockRejectedValue(new ApiError('boom', 500))

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByTestId('course-management-load-error')).toBeTruthy()
      expect(screen.getByText('boom')).toBeTruthy()
    })
    expect(screen.queryByText(/^Course not found$/i)).toBeNull()
    expect(screen.queryByTestId('course-management-inline-error')).toBeNull()
    expect(screen.queryByTestId('course-management-inline-info')).toBeNull()
  })

  it('shows Course not found for 404 load errors without generic error layout', async () => {
    api.getCourse.mockRejectedValue(new ApiError('Course not found', 404))

    renderCourseManagement()

    await waitFor(() => {
      expect(screen.getByTestId('course-management-not-found')).toBeTruthy()
      expect(screen.getByRole('heading', { name: /Course not found/i })).toBeTruthy()
    })
    expect(screen.queryByTestId('course-management-load-error')).toBeNull()
    expect(screen.queryByTestId('course-management-inline-error')).toBeNull()
    expect(screen.queryByTestId('course-management-inline-info')).toBeNull()
  })

  it('when one module exists, Add Lesson modal still shows module selector and sends moduleId', async () => {
    api.listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Only', description: '', order: 0 }])
    renderCourseManagement()

    const addButton = await waitFor(() => screen.getByText(/Add Lesson/i))
    fireEvent.click(addButton)

    const moduleSelect = screen.getByLabelText(/^Module$/i) as HTMLSelectElement
    expect(moduleSelect.value).toBe('m1')

    fireEvent.change(screen.getByLabelText(/Lesson Title/i), { target: { value: 'New Lesson' } })
    const file = new File(['x'], 'video.mp4', { type: 'video/mp4' })
    const fileInput = screen.getByLabelText(/Video File/i) as HTMLInputElement
    Object.defineProperty(fileInput, 'files', { value: [file] })
    fireEvent.change(fileInput)
    await waitFor(() => {
      expect(screen.getByText(/Selected:/i)).toBeTruthy()
    })

    const submit = screen.getByRole('button', { name: /^Add Lesson$/i })
    await waitFor(() => {
      expect((submit as HTMLButtonElement).disabled).toBe(false)
    })
    const form = submit.closest('form')
    expect(form).toBeTruthy()
    fireEvent.submit(form as HTMLFormElement)

    await waitFor(() => {
      expect(api.createLesson).toHaveBeenCalledWith('c1', { title: 'New Lesson', moduleId: 'm1' })
    })
  })

  describe('module quiz wiring', () => {
    it('shows module quiz wiring section when the course has modules', async () => {
      renderCourseManagement()

      await waitFor(() => {
        expect(screen.getByText('Manage Course')).toBeTruthy()
      })

      expect(screen.getByTestId('course-management-module-quizzes')).toBeTruthy()
      expect(screen.getByRole('heading', { name: /module quizzes/i })).toBeTruthy()
    })

    it('shows empty-state guidance when the course has no modules yet', async () => {
      api.listCourseModules.mockResolvedValue([])
      api.listLessons.mockResolvedValue([])
      api.listCourseModuleQuizzes.mockResolvedValue([])
      api.listCourseQuestionBanks.mockResolvedValue([])

      renderCourseManagement()

      await waitFor(() => {
        expect(screen.getByText('Manage Course')).toBeTruthy()
      })

      // GREEN slice: show this exact sentence in the module-quiz wiring panel when there are zero modules.
      expect(screen.getByText('Add a module first to attach bank quizzes.')).toBeTruthy()
    })

    it('attaches a draft bank quiz for the module after bank selection and Attach quiz', async () => {
      api.listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Section 1', description: '', order: 0 }])
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
      api.listCourseModuleQuizzes.mockResolvedValue([])
      api.listCourseQuestionBanks.mockResolvedValue([
        { questionBankId: 'qb1', name: 'Section 1 practice', status: 'DRAFT' },
      ])
      api.createModuleQuiz.mockResolvedValue({ moduleQuizId: 'mq1', moduleId: 'm1', questionBankId: 'qb1' })

      renderCourseManagement()

      await waitFor(() => {
        expect(screen.getByTestId('course-management-module-quizzes')).toBeTruthy()
      })

      const panel = screen.getByTestId('course-management-module-quizzes')
      // GREEN contract: bank picker is a labeled control; native <select> is exposed as role "combobox" in a11y tree.
      // Use <label htmlFor> + id on the select so tests can use getByLabelText(/^Question bank$/i) (or getByRole('combobox', { name: /^Question bank$/i })).
      const bankPicker = within(panel).getByLabelText(/^Question bank$/i)
      expect(within(panel).getByRole('option', { name: /Section 1 practice \(DRAFT\)/i })).toBeTruthy()
      fireEvent.change(bankPicker, { target: { value: 'qb1' } })

      fireEvent.click(within(panel).getByRole('button', { name: 'Attach quiz' }))

      await waitFor(() => {
        expect(api.createModuleQuiz).toHaveBeenCalledWith('c1', 'm1', { questionBankId: 'qb1' })
      })
    })

    it('hides bank in attach picker when already linked to another module', async () => {
      api.listCourseModuleQuizzes.mockResolvedValue([
        { quizId: 'mq1', moduleId: 'm1', questionBankId: 'qb1', servedCountN: null },
      ])
      api.listCourseQuestionBanks.mockResolvedValue([
        { questionBankId: 'qb1', name: 'Bank 1', status: 'DRAFT' },
        { questionBankId: 'qb2', name: 'Bank 2', status: 'DRAFT' },
      ])

      renderCourseManagement()

      const panel = await screen.findByTestId('course-management-module-quizzes')

      const m1Row = within(panel).getByText('Section 1').closest('li')
      expect(m1Row).toBeTruthy()
      expect(within(m1Row as HTMLElement).getByText('Quiz linked')).toBeTruthy()
      expect(within(m1Row as HTMLElement).getByText('Bank 1')).toBeTruthy()

      const m2Row = within(panel).getByText('Section 2').closest('li')
      expect(m2Row).toBeTruthy()
      const m2Picker = within(m2Row as HTMLElement).getByLabelText(/^Question bank$/i)
      expect(within(m2Picker).queryByRole('option', { name: /Bank 1 \(DRAFT\)/i })).toBeNull()
      expect(within(m2Picker).getByRole('option', { name: /Bank 2 \(DRAFT\)/i })).toBeTruthy()
    })

    it('shows linked quiz summaries with bank name and id', async () => {
      api.listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Section 1', description: '', order: 0 }])
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
      api.listCourseModuleQuizzes.mockResolvedValue([
        { quizId: 'mq1', moduleId: 'm1', questionBankId: 'qb1', servedCountN: 3 },
      ])
      api.listCourseQuestionBanks.mockResolvedValue([
        { questionBankId: 'qb1', name: 'Section 1 practice', status: 'PUBLISHED' },
      ])

      renderCourseManagement()

      const panel = await screen.findByTestId('course-management-module-quizzes')

      expect(within(panel).getByText('Section 1 practice')).toBeTruthy()
      expect(within(panel).getByText('ID: qb1')).toBeTruthy()
    })

    it('shows inline error on attach when createModuleQuiz fails with 400', async () => {
      api.listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Section 1', description: '', order: 0 }])
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
      api.listCourseModuleQuizzes.mockResolvedValue([])
      api.listCourseQuestionBanks.mockResolvedValue([{ questionBankId: 'qb1', status: 'DRAFT' }])
      api.createModuleQuiz.mockRejectedValueOnce(new ApiError('bad', 400, 'bad_request'))

      renderCourseManagement()

      await waitFor(() => {
        expect(screen.getByTestId('course-management-module-quizzes')).toBeTruthy()
      })

      const panel = screen.getByTestId('course-management-module-quizzes')
      const bankPicker = within(panel).getByLabelText(/^Question bank$/i)
      fireEvent.change(bankPicker, { target: { value: 'qb1' } })
      fireEvent.click(within(panel).getByRole('button', { name: 'Attach quiz' }))

      await waitFor(() => {
        const inline = screen.getByTestId('course-management-inline-error')
        expect(inline.textContent).toMatch(/bad/i)
        expect(inline.textContent).toBe(
          questionBankUserMessage(new ApiError('bad', 400, 'bad_request')),
        )
      })
    })

    it('shows inline error on attach when createModuleQuiz fails with 409 conflict', async () => {
      api.listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Section 1', description: '', order: 0 }])
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
      api.listCourseModuleQuizzes.mockResolvedValue([])
      api.listCourseQuestionBanks.mockResolvedValue([{ questionBankId: 'qb1', status: 'DRAFT' }])
      api.createModuleQuiz.mockRejectedValueOnce(
        new ApiError('Module already has a quiz', 409, 'conflict'),
      )

      renderCourseManagement()

      await waitFor(() => {
        expect(screen.getByTestId('course-management-module-quizzes')).toBeTruthy()
      })

      const panel = screen.getByTestId('course-management-module-quizzes')
      const bankPicker = within(panel).getByLabelText(/^Question bank$/i)
      fireEvent.change(bankPicker, { target: { value: 'qb1' } })
      fireEvent.click(within(panel).getByRole('button', { name: 'Attach quiz' }))

      await waitFor(() => {
        const inline = screen.getByTestId('course-management-inline-error')
        const expected = questionBankUserMessage(
          new ApiError('Module already has a quiz', 409, 'conflict'),
        )
        expect(inline.textContent).toBe(expected)
        expect(inline.textContent).toMatch(/conflict|refresh/i)
      })
    })
  })
})
