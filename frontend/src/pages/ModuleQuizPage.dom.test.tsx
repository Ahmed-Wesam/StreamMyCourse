/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../lib/api'
import { catalogApiUserMessage } from '../lib/questionBankErrors'
import ModuleQuizPage from './ModuleQuizPage'

const api = vi.hoisted(() => ({
  startModuleQuiz: vi.fn(),
  submitModuleQuiz: vi.fn(),
  listLessons: vi.fn(),
  getCourseProgress: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    startModuleQuiz: (...args: unknown[]) =>
      api.startModuleQuiz(...args) as ReturnType<typeof mod.startModuleQuiz>,
    submitModuleQuiz: (...args: unknown[]) =>
      api.submitModuleQuiz(...args) as ReturnType<typeof mod.submitModuleQuiz>,
    listLessons: (...args: unknown[]) => api.listLessons(...args) as ReturnType<typeof mod.listLessons>,
    getCourseProgress: (...args: unknown[]) =>
      api.getCourseProgress(...args) as ReturnType<typeof mod.getCourseProgress>,
  }
})

/** API order reversed vs naive binding order q1 → q2; options shuffled per question. */
const REVERSED_START_RESPONSE = {
  phase: 'in_progress' as const,
  moduleQuizId: 'mq1',
  moduleId: 'm1',
  servedCountN: 2,
  attemptId: 'att-1',
  attemptNumber: 1,
  questionIds: ['q2', 'q1'],
  questions: [
    {
      id: 'q2',
      promptText: 'Capital of France?',
      optionsJson: [
        { key: 'B', text: 'Paris' },
        { key: 'A', text: 'Berlin' },
      ],
    },
    {
      id: 'q1',
      promptText: 'What is 2 + 2?',
      optionsJson: [
        { key: 'B', text: '4' },
        { key: 'A', text: '3' },
      ],
    },
  ],
} as const

const LATEST_RESULTS_RESPONSE = {
  phase: 'latest_results' as const,
  moduleQuizId: 'mq1',
  moduleId: 'm1',
  servedCountN: 2,
  latestSubmission: {
    correctCount: 1,
    totalCount: 2,
    attemptNumber: 1,
    questions: [
      {
        id: 'q2',
        promptText: 'Capital of France?',
        selectedOptionKey: 'A',
        correctOptionKey: 'B',
        isCorrect: false,
      },
      {
        id: 'q1',
        promptText: 'What is 2 + 2?',
        selectedOptionKey: 'B',
        correctOptionKey: 'B',
        isCorrect: true,
      },
    ],
  },
} as const

type QuizEntry = string | { pathname: string; state?: { returnTo?: string } }

function renderModuleQuiz(entry: QuizEntry = '/courses/c1/modules/m1/quiz') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/courses/:courseId/modules/:moduleId/quiz" element={<ModuleQuizPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

function optionKeysInFieldset(fieldset: HTMLElement): string[] {
  return within(fieldset)
    .getAllByRole('radio')
    .map((input) => (input as HTMLInputElement).value)
}

function optionLabelsInFieldset(fieldset: HTMLElement): string[] {
  return within(fieldset)
    .getAllByRole('radio')
    .map((input) => input.closest('label')?.textContent?.trim() ?? '')
}

describe('ModuleQuizPage', () => {
  beforeEach(() => {
    api.startModuleQuiz.mockReset()
    api.submitModuleQuiz.mockReset()
    api.listLessons.mockReset()
    api.getCourseProgress.mockReset()
    api.startModuleQuiz.mockResolvedValue(REVERSED_START_RESPONSE)
    api.listLessons.mockResolvedValue([
      { id: 'l1', title: 'Lesson 1', order: 0, moduleId: 'm1', moduleOrder: 0, videoStatus: 'ready' as const },
    ])
    api.getCourseProgress.mockResolvedValue({
      courseId: 'c1',
      totalReadyLessons: 1,
      completedCount: 0,
      percentComplete: 0,
      lessons: [],
    })
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('Back to course links to the lesson player when returnTo is in location state', async () => {
    renderModuleQuiz({
      pathname: '/courses/c1/modules/m1/quiz',
      state: { returnTo: '/courses/c1/lessons/l1' },
    })

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Back to course/i })).toBeTruthy()
    })

    expect(screen.getByRole('link', { name: /Back to course/i }).getAttribute('href')).toBe(
      '/courses/c1/lessons/l1',
    )
  })

  it('Back to course resolves to a lesson in the module when returnTo is absent', async () => {
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Back to course/i }).getAttribute('href')).toBe(
        '/courses/c1/lessons/l1',
      )
    })
  })

  it('calls startModuleQuiz on mount with route params', async () => {
    renderModuleQuiz()

    await waitFor(() => {
      expect(api.startModuleQuiz).toHaveBeenCalledWith('c1', 'm1')
    })
  })

  it('renders questions and options in API order (not binding order)', async () => {
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })

    expect(
      screen.getByText(
        /If you leave this page before submitting, your selected answers will be lost./i,
      ),
    ).toBeTruthy()

    const fieldsets = screen.getAllByRole('group')
    expect(fieldsets).toHaveLength(2)

    expect(within(fieldsets[0]!).getByText('Capital of France?')).toBeTruthy()
    expect(within(fieldsets[1]!).getByText('What is 2 + 2?')).toBeTruthy()

    expect(optionKeysInFieldset(fieldsets[0]!)).toEqual(['B', 'A'])
    expect(optionLabelsInFieldset(fieldsets[0]!)).toEqual(['Paris', 'Berlin'])

    expect(optionKeysInFieldset(fieldsets[1]!)).toEqual(['B', 'A'])
    expect(optionLabelsInFieldset(fieldsets[1]!)).toEqual(['4', '3'])
  })

  it('keeps Submit disabled until every question has a selection', async () => {
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })

    const submit = screen.getByRole('button', { name: /submit answers/i }) as HTMLButtonElement
    expect(submit.disabled).toBe(true)
    const helperText = screen.getByText(/answer every question before submitting/i)
    expect(helperText).toBeTruthy()
    expect(submit.getAttribute('aria-describedby')).toBe(helperText.id)

    const fieldsets = screen.getAllByRole('group')
    fireEvent.click(within(fieldsets[0]!).getAllByRole('radio')[0]!)
    expect(submit.disabled).toBe(true)
    expect(screen.getByText(/answer every question before submitting/i)).toBeTruthy()

    fireEvent.click(within(fieldsets[1]!).getAllByRole('radio')[0]!)
    expect(submit.disabled).toBe(false)
    expect(screen.queryByText(/answer every question before submitting/i)).toBeNull()
  })

  it('renders latest submission summary and Try again without MCQ controls', async () => {
    api.startModuleQuiz.mockResolvedValue(LATEST_RESULTS_RESPONSE)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText(/Score 1 \/ 2/)).toBeTruthy()
    })

    expect(screen.getByText(/These are your latest submitted results./i)).toBeTruthy()
    expect(
      screen.getByText(
        /Trying again draws a new set of questions from the bank and reshuffles them./i,
      ),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: /^Try again$/i })).toBeTruthy()
    expect(screen.queryAllByRole('radio')).toHaveLength(0)
    expect(screen.queryByRole('button', { name: /submit answers/i })).toBeNull()
  })

  it('Try again calls startModuleQuiz with retake: true', async () => {
    api.startModuleQuiz.mockResolvedValueOnce(LATEST_RESULTS_RESPONSE).mockResolvedValue(REVERSED_START_RESPONSE)

    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText(/Score 1 \/ 2/)).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: /^Try again$/i }))

    await waitFor(() => {
      expect(api.startModuleQuiz).toHaveBeenLastCalledWith('c1', 'm1', { retake: true })
    })

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })
    expect(screen.getByRole('button', { name: /submit answers/i })).toBeTruthy()
  })

  it('submits attemptId and full answers map on Submit', async () => {
    api.submitModuleQuiz.mockResolvedValue({
      attemptId: 'att-1',
      attemptNumber: 1,
      correctCount: 2,
      totalCount: 2,
      questions: LATEST_RESULTS_RESPONSE.latestSubmission.questions,
    })

    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })

    const fieldsets = screen.getAllByRole('group')
    fireEvent.click(within(fieldsets[0]!).getAllByRole('radio')[0]!)
    fireEvent.click(within(fieldsets[1]!).getAllByRole('radio')[0]!)

    fireEvent.click(screen.getByRole('button', { name: /submit answers/i }))

    await waitFor(() => {
      expect(api.submitModuleQuiz).toHaveBeenCalledWith('c1', 'm1', {
        attemptId: 'att-1',
        answers: { q2: 'B', q1: 'B' },
      })
    })

    await waitFor(() => {
      expect(screen.getAllByText(/Your answer:/)).toHaveLength(2)
      expect(screen.getByRole('button', { name: /^Try again$/i })).toBeTruthy()
    })
    expect(screen.queryAllByRole('radio')).toHaveLength(0)
  })

  it('shows catalog API user message when startModuleQuiz rejects with ApiError 404', async () => {
    const err = new ApiError('Module not found', 404)
    api.startModuleQuiz.mockRejectedValueOnce(err)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText(catalogApiUserMessage(err))).toBeTruthy()
    })
    expect(screen.queryByText('Capital of France?')).toBeNull()
  })

  it('shows catalog API user message when startModuleQuiz rejects with ApiError 409', async () => {
    const err = new ApiError('Conflict', 409)
    api.startModuleQuiz.mockRejectedValueOnce(err)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText(catalogApiUserMessage(err))).toBeTruthy()
    })
  })

  it('shows catalog API user message when startModuleQuiz rejects with ApiError 400', async () => {
    const err = new ApiError('Answers incomplete', 400)
    api.startModuleQuiz.mockRejectedValueOnce(err)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText(catalogApiUserMessage(err))).toBeTruthy()
    })
  })

  it('shows catalog API user message when submitModuleQuiz rejects with ApiError 404', async () => {
    const err = new ApiError('Attempt not found', 404)
    api.submitModuleQuiz.mockRejectedValueOnce(err)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })

    const fieldsets = screen.getAllByRole('group')
    fireEvent.click(within(fieldsets[0]!).getAllByRole('radio')[0]!)
    fireEvent.click(within(fieldsets[1]!).getAllByRole('radio')[0]!)
    fireEvent.click(screen.getByRole('button', { name: /submit answers/i }))

    await waitFor(() => {
      expect(screen.getByText(catalogApiUserMessage(err))).toBeTruthy()
    })
  })

  it('shows catalog API user message when submitModuleQuiz rejects with ApiError 409', async () => {
    const err = new ApiError('Stale attempt', 409)
    api.submitModuleQuiz.mockRejectedValueOnce(err)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })

    const fieldsets = screen.getAllByRole('group')
    fireEvent.click(within(fieldsets[0]!).getAllByRole('radio')[0]!)
    fireEvent.click(within(fieldsets[1]!).getAllByRole('radio')[0]!)
    fireEvent.click(screen.getByRole('button', { name: /submit answers/i }))

    await waitFor(() => {
      expect(screen.getByText(catalogApiUserMessage(err))).toBeTruthy()
    })
  })

  it('shows catalog API user message when submitModuleQuiz rejects with ApiError 400', async () => {
    const err = new ApiError('Invalid payload', 400)
    api.submitModuleQuiz.mockRejectedValueOnce(err)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })

    const fieldsets = screen.getAllByRole('group')
    fireEvent.click(within(fieldsets[0]!).getAllByRole('radio')[0]!)
    fireEvent.click(within(fieldsets[1]!).getAllByRole('radio')[0]!)
    fireEvent.click(screen.getByRole('button', { name: /submit answers/i }))

    await waitFor(() => {
      expect(screen.getByText(catalogApiUserMessage(err))).toBeTruthy()
    })
  })

  it('shows catalog API user message when retake startModuleQuiz rejects with ApiError 409', async () => {
    const err = new ApiError('Cannot start retake', 409)
    api.startModuleQuiz.mockResolvedValueOnce(LATEST_RESULTS_RESPONSE).mockRejectedValueOnce(err)
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText(/Score 1 \/ 2/)).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: /^Try again$/i }))

    await waitFor(() => {
      expect(screen.getByText(catalogApiUserMessage(err))).toBeTruthy()
    })
  })
})
