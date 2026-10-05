/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api/client'
import { DEFAULT_SECTION_HEADINGS } from '../lib/course-page'
import {
  courseDetailLifetimePill,
  courseDetailNoAccessPrompt,
  courseDetailSignInPrompt,
} from '../lib/marketing/courseDetailShellCopy'
import CourseDetailPage from './CourseDetailPage'

const api = vi.hoisted(() => ({
  getCourse: vi.fn(),
  listLessons: vi.fn(),
  listCourseModules: vi.fn(),
  getCourseProgress: vi.fn(),
  hasSignedInIdToken: vi.fn(),
  updateLessonProgress: vi.fn(),
}))

const listPublishedCourses = vi.hoisted(() => vi.fn())

vi.mock('../lib/api/public-catalog', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api/public-catalog')
  return {
    ...mod,
    listPublishedCourses: (...args: unknown[]) =>
      listPublishedCourses(...args) as ReturnType<typeof mod.listPublishedCourses>,
  }
})

vi.mock('../lib/api/catalog', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api/catalog')
  return {
    ...mod,
    getCourse: (...args: unknown[]) => api.getCourse(...args) as ReturnType<typeof mod.getCourse>,
    listLessons: (...args: unknown[]) => api.listLessons(...args) as ReturnType<typeof mod.listLessons>,
    listCourseModules: (...args: unknown[]) =>
      api.listCourseModules(...args) as ReturnType<typeof mod.listCourseModules>,
    getCourseProgress: (...args: unknown[]) =>
      api.getCourseProgress(...args) as ReturnType<typeof mod.getCourseProgress>,
    updateLessonProgress: (...args: unknown[]) =>
      api.updateLessonProgress(...args) as ReturnType<typeof mod.updateLessonProgress>,
  }
})

vi.mock('../lib/api/session', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api/session')
  return {
    ...mod,
    hasSignedInIdToken: (...args: unknown[]) =>
      api.hasSignedInIdToken(...args) as ReturnType<typeof mod.hasSignedInIdToken>,
  }
})

function renderCourseDetail(path = '/courses/c1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/courses/:courseId" element={<CourseDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CourseDetailPage', () => {
  beforeEach(() => {
    api.getCourse.mockReset()
    api.listLessons.mockReset()
    api.listCourseModules.mockReset()
    api.getCourseProgress.mockReset()
    api.hasSignedInIdToken.mockReset()
    api.updateLessonProgress.mockReset()
    listPublishedCourses.mockReset()

    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
    })
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'First Lesson',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
      {
        id: 'l2',
        title: 'Second Lesson',
        order: 1,
        moduleId: 'm2',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 200,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'Section 1', description: '', order: 0 },
      { id: 'm2', title: 'Section 2', description: '', order: 1 },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 0,
      percentComplete: 0,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 0 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })
    api.hasSignedInIdToken.mockResolvedValue(true)
    api.updateLessonProgress.mockResolvedValue({
      ok: true,
      lessonProgress: { lessonId: 'l1', completed: true, lastPositionSec: 0 },
    })
    listPublishedCourses.mockResolvedValue([
      { id: 'c1', title: 'Test Course', description: 'Test Description' },
      { id: 'c2', title: 'Course Two', description: 'Two' },
    ])
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders course title', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Test Course' })).toBeTruthy()
    })
  })

  it('renders list of lessons', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.getByText('Second Lesson')).toBeTruthy()
  })

  it('groups lessons by module and shows module titles', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Section 1')).toBeTruthy()
    })
    expect(screen.getByText('Section 2')).toBeTruthy()
    expect(screen.getByText('First Lesson')).toBeTruthy()
    expect(screen.getByText('Second Lesson')).toBeTruthy()
  })

  it('renders orphan moduleId lessons under an Unsorted section', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'In Module One',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
      {
        id: 'l2',
        title: 'In Module Two',
        order: 1,
        moduleId: 'm2',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 200,
      },
      {
        id: 'l3',
        title: 'Orphan Lesson',
        order: 1,
        moduleId: 'm-unknown',
        moduleOrder: 2,
        videoStatus: 'ready',
        duration: 150,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'Section 1', description: '', order: 0 },
      { id: 'm2', title: 'Section 2', description: '', order: 1 },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 3,
      completedCount: 0,
      percentComplete: 0,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 0 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
        { lessonId: 'l3', completed: false, lastPositionSec: 0 },
      ],
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('In Module One')).toBeTruthy()
    })
    expect(screen.getByText('In Module Two')).toBeTruthy()
    expect(screen.getByText('Orphan Lesson')).toBeTruthy()
    const unsortedHeadings = screen.getAllByText('Unsorted')
    expect(unsortedHeadings.length).toBeGreaterThan(0)
  })

  it('does not render Lesson N subtitle (order is per-module)', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.queryByText('Lesson 1')).toBeNull()
  })

  it('shows Start Learning button for new course', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Start Learning')).toBeTruthy()
    })
  })

  it('shows Resume Learning button when progress exists', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 0,
      percentComplete: 25,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 50 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Resume Learning')).toBeTruthy()
    })
  })

  it('shows neutral no-access copy without checkout when signed in without access', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      hasAccess: false,
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(courseDetailNoAccessPrompt)).toBeTruthy()
    })
    expect(screen.queryByText(/Subscribe/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /checkout|subscribe/i })).toBeNull()
  })

  it('shows lesson action menu trigger when enrolled', async () => {
    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: /Lesson actions: First Lesson/i })).toBeTruthy()
  })

  it('does not show lesson action menu trigger when not enrolled', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: false,
    })
    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /Lesson actions:/i })).toBeNull()
  })

  it('marks lesson complete via menu action', async () => {
    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })
    fireEvent.click(screen.getByRole('button', { name: /Lesson actions: First Lesson/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Mark as complete/i }))
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l1', {
        lastPositionSec: 0,
        durationSec: 100,
        markComplete: true,
      })
    })
  })

  it('marks lesson incomplete via menu action when already completed', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 100 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })
    api.updateLessonProgress.mockResolvedValue({
      ok: true,
      lessonProgress: { lessonId: 'l1', completed: false, lastPositionSec: 0 },
    })

    renderCourseDetail()
    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: /Lesson actions: First Lesson/i }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Mark as incomplete/i }))
    await waitFor(() => {
      expect(api.updateLessonProgress).toHaveBeenCalledWith('c1', 'l1', {
        lastPositionSec: 0,
        durationSec: 100,
        markIncomplete: true,
      })
    })
  })

  it('shows Enroll Now for anonymous users', async () => {
    api.hasSignedInIdToken.mockResolvedValue(false)

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getAllByRole('link', { name: /enroll now/i }).length).toBeGreaterThan(0)
    })
    expect(screen.queryByText(courseDetailSignInPrompt)).toBeNull()
  })

  it('links to first lesson when Start Learning clicked', async () => {
    renderCourseDetail()

    const startButton = await waitFor(() => screen.getByText('Start Learning'))
    const href = startButton.closest('a')?.getAttribute('href')
    expect(href).toBe('/courses/c1/lessons/l1')
  })

  it('links to lesson with resume time when Resume Learning clicked', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 0,
      percentComplete: 25,
      lessons: [
        { lessonId: 'l1', completed: false, lastPositionSec: 50 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
      ],
    })

    renderCourseDetail()

    const resumeButton = await waitFor(() => screen.getByText('Resume Learning'))
    const href = resumeButton.closest('a')?.getAttribute('href')
    expect(href).toBe('/courses/c1/lessons/l1?t=50')
  })

  it('Resume href skips locked module incomplete lesson for later unlocked lesson', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'L1',
        order: 0,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
      {
        id: 'l2',
        title: 'L2',
        order: 0,
        moduleId: 'm2',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 100,
      },
      {
        id: 'l3',
        title: 'L3',
        order: 0,
        moduleId: 'm3',
        moduleOrder: 2,
        videoStatus: 'ready',
        duration: 100,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'M1', description: '', order: 0 },
      { id: 'm2', title: 'M2', description: '', order: 1, locked: true },
      { id: 'm3', title: 'M3', description: '', order: 2 },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 3,
      completedCount: 1,
      percentComplete: 33,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 100 },
        { lessonId: 'l2', completed: false, lastPositionSec: 0 },
        { lessonId: 'l3', completed: false, lastPositionSec: 0 },
      ],
    })

    renderCourseDetail()

    const startButton = await waitFor(() => screen.getByText('Start Learning'))
    const href = startButton.closest('a')?.getAttribute('href')
    expect(href).toBe('/courses/c1/lessons/l3')
    expect(href).not.toContain('l2')
  })

  it('Resume href points to quiz when incomplete lessons are only in locked modules', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'L1',
        order: 0,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      {
        id: 'm1',
        title: 'M1',
        description: '',
        order: 0,
        locked: true,
        moduleQuiz: { available: true, servedCountN: 5, passed: false },
      },
      {
        id: 'm2',
        title: 'M2',
        description: '',
        order: 1,
        moduleQuiz: { available: true, servedCountN: 5, passed: false },
      },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [{ lessonId: 'l1', completed: false, lastPositionSec: 0 }],
    })

    renderCourseDetail()

    const button = await waitFor(() => screen.getByText('Start Learning'))
    const href = button.closest('a')?.getAttribute('href')
    expect(href).toBe('/courses/c1/modules/m2/quiz')
  })

  it('disables Resume when incomplete lessons are locked and no quiz fallback exists', async () => {
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'L1',
        order: 0,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
      },
    ])
    api.listCourseModules.mockResolvedValue([
      { id: 'm1', title: 'M1', description: '', order: 0, locked: true },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [{ lessonId: 'l1', completed: false, lastPositionSec: 0 }],
    })

    renderCourseDetail()

    const button = await waitFor(() => screen.getByText('Start Learning'))
    expect(button.closest('a')).toBeNull()
    expect(button.closest('span')?.className).toMatch(/cursor-not-allowed/)
  })

  it('shows lesson thumbnails with progress bars', async () => {
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 2,
      completedCount: 1,
      percentComplete: 50,
      lessons: [
        { lessonId: 'l1', completed: true, lastPositionSec: 100 },
        { lessonId: 'l2', completed: false, lastPositionSec: 30 },
      ],
    })

    renderCourseDetail()

    await waitFor(() => {
      const progressBars = screen.getAllByRole('progressbar')
      expect(progressBars.length).toBeGreaterThan(0)
    })
  })

  it('renders breadcrumb Home > Courses > course title', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('navigation', { name: /breadcrumb/i })).toBeTruthy()
    })
    expect(screen.getByRole('link', { name: 'Home' }).getAttribute('href')).toBe('/')
    expect(screen.getByRole('link', { name: 'Courses' }).getAttribute('href')).toBe('/courses')
    const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(breadcrumb.textContent).toContain('Test Course')
  })

  it('does not render placeholder or FAQ shell headings', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Test Course' })).toBeTruthy()
    })

    expect(screen.queryByRole('heading', { level: 2, name: 'Common questions' })).toBeNull()
    expect(
      screen.queryByText('Learning outcomes for this course will be listed here.'),
    ).toBeNull()
    expect(screen.queryByText('Audience details for this course will appear here.')).toBeNull()
  })

  it('renders filled problem and outcomes sections and omits empty audience', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
      problem: {
        items: ['Choosing the wrong statistical test wastes months of work.'],
        calloutTitle: 'The fix',
        calloutBody: 'Follow a decision framework.',
      },
      outcomes: {
        lead: 'Run independent analyses in SPSS.',
        items: ['Interpret p-values correctly'],
      },
      audience: { heading: '   ', items: [] },
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(
        screen.getByRole('heading', {
          level: 2,
          name: DEFAULT_SECTION_HEADINGS.problem,
        }),
      ).toBeTruthy()
    })
    expect(screen.getByText('Choosing the wrong statistical test wastes months of work.')).toBeTruthy()
    expect(screen.getByText('The fix')).toBeTruthy()
    expect(screen.getByText('Run independent analyses in SPSS.')).toBeTruthy()
    expect(screen.getByText('Interpret p-values correctly')).toBeTruthy()
    expect(
      screen.queryByRole('heading', { level: 2, name: DEFAULT_SECTION_HEADINGS.audience }),
    ).toBeNull()
  })

  it('renders hero subtitle, level, and estimated hours pills', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Fallback description',
      status: 'PUBLISHED',
      enrolled: true,
      subtitle: 'Master SPSS from scratch',
      level: 'Intermediate',
      estimatedHours: 12,
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('Master SPSS from scratch')).toBeTruthy()
    })
    const hero = screen.getByLabelText('Course hero')
    expect(within(hero).getByText('Intermediate')).toBeTruthy()
    expect(within(hero).getByText('~12 Hours')).toBeTruthy()
    expect(within(hero).queryByText('Fallback description')).toBeNull()
  })

  it('renders the manuscript note under the Scientific Writing curriculum', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Scientific Writing',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: 'A Manuscript Is More Than Writing' })).toBeTruthy()
    })
    expect(
      screen.getByText(
        'Successful publication requires more than writing individual sections. Researchers must understand reporting standards, journal expectations, reviewer feedback, submission requirements, and scientific communication principles — this course addresses the complete publication process.',
      ),
    ).toBeTruthy()
  })

  it('renders the Systematic Reviews callout paragraph when the stored problem has no callout body', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Systematic Reviews & Meta-Analysis',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
      problem: {
        heading: 'Why Most Systematic Reviews Fail',
        calloutTitle: 'Stop Following Random YouTube Tutorials',
        items: ['Poor search strategies'],
      },
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: 'Stop Following Random YouTube Tutorials' })).toBeTruthy()
    })
    expect(
      screen.getByText(
        'Learn a structured framework used in publishable systematic reviews and meta-analyses — built on PRISMA, registered protocols, and the standards journals actually expect.',
      ),
    ).toBeTruthy()
  })

  it('renders the prototype research-journey heading for Research Methodology', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Research Methodology',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 2, name: 'Part of a Bigger Research Journey' }),
      ).toBeTruthy()
    })
  })

  it('renders the static research journey steps for a prototype course', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Statistics & SPSS',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('YOU ARE HERE')).toBeTruthy()
    })
    expect(screen.getByRole('heading', { level: 4, name: 'Statistics & SPSS' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 4, name: 'Research Team Eligibility' })).toBeTruthy()
    expect(screen.getByText(/Complete all four courses to become eligible/i)).toBeTruthy()
  })

  it('shows enroll CTA band with checkout link when viewer lacks access', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      hasAccess: false,
      enrollCta: {
        heading: 'Ready to enroll?',
        body: 'Get lifetime access to every lesson.',
        extraLine: 'Bundle available at checkout.',
      },
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Ready to enroll?' })).toBeTruthy()
    })
    expect(screen.getByText('Get lifetime access to every lesson.')).toBeTruthy()
    const enrollLinks = screen.getAllByRole('link', { name: /enroll/i })
    expect(
      enrollLinks.some((link) => link.getAttribute('href') === '/checkout?productType=course&courseId=c1'),
    ).toBe(true)
  })

  it('omits enroll CTA band when the viewer owns the course', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
      enrollCta: {
        heading: 'Ready to enroll?',
        body: 'Should not show when owned.',
      },
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Test Course' })).toBeTruthy()
    })
    expect(screen.queryByRole('heading', { level: 2, name: 'Ready to enroll?' })).toBeNull()
    expect(screen.queryByRole('link', { name: /enroll/i })).toBeNull()
  })

  it('renders lifetime access pill and no dollar amounts', async () => {
    const { container } = renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(courseDetailLifetimePill)).toBeTruthy()
    })
    expect(container.textContent ?? '').not.toMatch(/\$/)
  })

  it('renders the live JOD amount from priceAmountMinor', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: false,
      priceAmountMinor: 50_000,
    })

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getAllByText(/JOD\s*50/).length).toBeGreaterThan(0)
    })
  })

  it('does not render mock instructor name or pricing band', async () => {
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Test Course' })).toBeTruthy()
    })
    expect(screen.queryByText('Dr. Bahaa Aburayya')).toBeNull()
    expect(screen.queryByTestId('course-pricing')).toBeNull()
    expect(screen.queryByRole('region', { name: /pricing/i })).toBeNull()
  })

  it('renders the hero and curriculum with id curriculum', async () => {
    renderCourseDetail()

    const heroHeading = await waitFor(() => screen.getByRole('heading', { level: 1, name: 'Test Course' }))
    expect(heroHeading).toBeTruthy()

    const curriculum = document.getElementById('curriculum')
    expect(curriculum).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Complete Curriculum' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: /course stats/i })).toBeNull()
  })

  it('shows loading state initially', () => {
    renderCourseDetail()
    expect(document.querySelector('.animate-pulse')).toBeTruthy()
  })

  it('shows error message when course fails to load', async () => {
    api.getCourse.mockRejectedValue(new Error('Failed to fetch'))

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/This course could not be loaded/i)).toBeTruthy()
    })
    expect(screen.getByRole('heading', { level: 1, name: 'Unable to load course' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: /course stats/i })).toBeNull()
  })

  it('shows course not found when getCourse returns null', async () => {
    api.getCourse.mockResolvedValue(null as never)

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/That course was not found/i)).toBeTruthy()
    })
    expect(screen.getByRole('heading', { level: 1, name: 'Course not found' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: /course stats/i })).toBeNull()
    expect(screen.queryByText('First Lesson')).toBeNull()
  })

  it('shows error banner and does not render lessons when listCourseModules fails', async () => {
    api.listCourseModules.mockRejectedValue(new Error('Modules failed'))
    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/This course could not be loaded/i)).toBeTruthy()
    })
    expect(screen.getByRole('heading', { level: 1, name: 'Unable to load course' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: /course stats/i })).toBeNull()
    expect(screen.queryByText('First Lesson')).toBeNull()
    expect(screen.queryByText('Second Lesson')).toBeNull()
  })

  it('shows No lessons message when course has no lessons', async () => {
    api.listLessons.mockResolvedValue([])

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText(/No lessons yet/i)).toBeTruthy()
    })
  })

  it('omits non-https course and lesson thumbnail images', async () => {
    api.getCourse.mockResolvedValue({
      id: 'c1',
      title: 'Test Course',
      description: 'Test Description',
      status: 'PUBLISHED',
      enrolled: true,
      thumbnailUrl: 'http://insecure.example/thumb.jpg',
    })
    api.listLessons.mockResolvedValue([
      {
        id: 'l1',
        title: 'First Lesson',
        order: 1,
        moduleId: 'm1',
        moduleOrder: 0,
        videoStatus: 'ready',
        duration: 100,
        thumbnailUrl: 'javascript:alert(1)',
      },
      {
        id: 'l2',
        title: 'Second Lesson',
        order: 1,
        moduleId: 'm2',
        moduleOrder: 1,
        videoStatus: 'ready',
        duration: 200,
        thumbnailUrl: 'https://cdn.example/lesson-2.jpg',
      },
    ])

    renderCourseDetail()

    await waitFor(() => {
      expect(screen.getByText('First Lesson')).toBeTruthy()
    })

    const imgs = Array.from(document.querySelectorAll('img'))
    expect(imgs.some((img) => img.getAttribute('src') === 'http://insecure.example/thumb.jpg')).toBe(false)
    expect(imgs.some((img) => img.getAttribute('src')?.startsWith('javascript:'))).toBe(false)
    expect(imgs.some((img) => img.getAttribute('src') === 'https://cdn.example/lesson-2.jpg')).toBe(true)
  })

  describe('module quiz badge', () => {
    it('shows passive Module quiz badge when enrolled and moduleQuiz.available', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.getByText('Module quiz')).toBeTruthy()
    })

    it('shows Start quiz link when enrolled and moduleQuiz.available', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /start quiz/i })).toBeTruthy()
      })
      const startLink = screen.getByRole('link', { name: /start quiz/i })
      expect(startLink.getAttribute('href')).toBe('/courses/c1/modules/m1/quiz')
    })

    it('shows a quiz-only module when it has no lessons', async () => {
      api.listLessons.mockResolvedValue([])
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Quiz Only Section', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Quiz Only Section')).toBeTruthy()
      })
      expect(screen.getByRole('link', { name: /start quiz/i }).getAttribute('href')).toBe(
        '/courses/c1/modules/m1/quiz',
      )
      expect(screen.queryByText(/No lessons yet/i)).toBeNull()
    })

    it('navigates to module quiz route when Start quiz is clicked', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      const QuizStub = () => <div data-testid="quiz-page">Quiz shell</div>
      const router = createMemoryRouter(
        [
          { path: '/courses/:courseId', element: <CourseDetailPage /> },
          { path: '/courses/:courseId/modules/:moduleId/quiz', element: <QuizStub /> },
        ],
        { initialEntries: ['/courses/c1'] },
      )
      render(<RouterProvider router={router} />)

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /start quiz/i })).toBeTruthy()
      })
      fireEvent.click(screen.getByRole('link', { name: /start quiz/i }))

      await waitFor(() => {
        expect(screen.getByTestId('quiz-page')).toBeTruthy()
      })
    })

    it('does not show Module quiz badge when moduleQuiz is absent', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0 },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.queryByText('Module quiz')).toBeNull()
    })

    it('does not show Module quiz badge when not enrolled', async () => {
      api.getCourse.mockResolvedValue({
        id: 'c1',
        title: 'Test Course',
        description: 'Test Description',
        status: 'PUBLISHED',
        enrolled: false,
      })
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: true, servedCountN: 2 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.queryByText('Module quiz')).toBeNull()
    })

    it('shows unlock hint instead of Start quiz when module is locked', async () => {
      api.listCourseModules.mockResolvedValue([
        {
          id: 'm1',
          title: 'Section 1',
          description: '',
          order: 0,
          locked: true,
          moduleQuiz: { available: true, servedCountN: 2, passPercent: 70 },
        },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText(/Complete the prior module quiz to unlock/i)).toBeTruthy()
      })
      expect(screen.queryByRole('link', { name: /start quiz/i })).toBeNull()
    })

    it('does not show Module quiz badge when moduleQuiz.available is false', async () => {
      api.listCourseModules.mockResolvedValue([
        { id: 'm1', title: 'Section 1', description: '', order: 0, moduleQuiz: { available: false, servedCountN: 0 } },
        { id: 'm2', title: 'Section 2', description: '', order: 1 },
      ])

      renderCourseDetail()

      await waitFor(() => {
        expect(screen.getByText('Section 1')).toBeTruthy()
      })
      expect(screen.queryByText('Module quiz')).toBeNull()
    })
  })

  it('clears hero and lesson list when route changes and the new course fails to load', async () => {
    api.getCourse.mockImplementation((courseId: string) => {
      if (courseId === 'c1') {
        return Promise.resolve({
          id: 'c1',
          title: 'Stale Hero Title',
          description: 'Test Description',
          status: 'PUBLISHED',
          enrolled: true,
        })
      }
      return Promise.reject(new ApiError('boom', 500))
    })

    const router = createMemoryRouter(
      [{ path: '/courses/:courseId', element: <CourseDetailPage /> }],
      { initialEntries: ['/courses/c1'] },
    )
    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Stale Hero Title' })).toBeTruthy()
    })
    expect(screen.getByText('First Lesson')).toBeTruthy()

    await router.navigate('/courses/c2')

    await waitFor(() => {
      expect(screen.getByText(/This course could not be loaded/i)).toBeTruthy()
    })
    await waitFor(() => {
      expect(screen.queryByText('Stale Hero Title')).toBeNull()
    })
    expect(screen.queryByText('First Lesson')).toBeNull()
  })
})
