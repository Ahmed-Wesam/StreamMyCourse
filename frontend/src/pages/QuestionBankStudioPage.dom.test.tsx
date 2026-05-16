/**
 * @vitest-environment jsdom
 *
 * Handoff (GREEN): expected `data-testid` hooks
 * - `question-bank-studio-loaded` — set when bank + questions list fetches complete
 * - `studio-question-prompt` — prompt input/textarea
 * - `studio-option-key-{n}` / `studio-option-text-{n}` — at least rows 0 and 1 for MCQ options
 * - `studio-add-option` — append another option row if fewer than two are shown initially
 * - `studio-correct-select` — `<select>` whose value is the chosen option key
 * - `studio-add-question-submit` — submit control for createQuestionBankQuestion
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import QuestionBankStudioPage from './QuestionBankStudioPage'

const api = vi.hoisted(() => ({
  listCourseQuestionBanks: vi.fn(),
  listQuestionBankQuestions: vi.fn(),
  createQuestionBankQuestion: vi.fn(),
  updateQuestionBankQuestion: vi.fn(),
  deleteQuestionBankQuestion: vi.fn(),
  publishQuestionBank: vi.fn(),
  listCourseModuleQuizzes: vi.fn(),
}))

const mockNavigate = vi.fn()
const mockRouteParams = vi.hoisted(() => ({ courseId: 'c1', bankId: 'qb1' }))

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
    listCourseQuestionBanks: (...args: unknown[]) =>
      api.listCourseQuestionBanks(...args) as ReturnType<typeof mod.listCourseQuestionBanks>,
    listQuestionBankQuestions: (...args: unknown[]) =>
      api.listQuestionBankQuestions(...args) as ReturnType<typeof mod.listQuestionBankQuestions>,
    createQuestionBankQuestion: (...args: unknown[]) =>
      api.createQuestionBankQuestion(...args) as ReturnType<typeof mod.createQuestionBankQuestion>,
    updateQuestionBankQuestion: (...args: unknown[]) =>
      api.updateQuestionBankQuestion(...args) as ReturnType<typeof mod.updateQuestionBankQuestion>,
    deleteQuestionBankQuestion: (...args: unknown[]) =>
      api.deleteQuestionBankQuestion(...args) as ReturnType<typeof mod.deleteQuestionBankQuestion>,
    publishQuestionBank: (...args: unknown[]) =>
      api.publishQuestionBank(...args) as ReturnType<typeof mod.publishQuestionBank>,
    listCourseModuleQuizzes: (...args: unknown[]) =>
      api.listCourseModuleQuizzes(...args) as ReturnType<typeof mod.listCourseModuleQuizzes>,
  }
})

function renderStudio(initialEntries: string[] = ['/courses/c1/question-banks/qb1']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route
          path="/courses/:courseId/question-banks/:bankId"
          element={<QuestionBankStudioPage />}
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('QuestionBankStudioPage', () => {
  beforeEach(() => {
    api.listCourseQuestionBanks.mockReset()
    api.listQuestionBankQuestions.mockReset()
    api.createQuestionBankQuestion.mockReset()
    api.updateQuestionBankQuestion.mockReset()
    api.deleteQuestionBankQuestion.mockReset()
    api.publishQuestionBank.mockReset()
    api.listCourseModuleQuizzes.mockReset()
    mockNavigate.mockReset()
    mockRouteParams.courseId = 'c1'
    mockRouteParams.bankId = 'qb1'

    api.listCourseQuestionBanks.mockResolvedValue([{ questionBankId: 'qb1', status: 'DRAFT' }])
    api.listQuestionBankQuestions.mockResolvedValue([])
    api.createQuestionBankQuestion.mockResolvedValue({ questionId: 'q-new' })
    api.updateQuestionBankQuestion.mockResolvedValue({ status: 'updated' })
    api.deleteQuestionBankQuestion.mockResolvedValue({ status: 'deleted' })
    api.publishQuestionBank.mockResolvedValue({ status: 'PUBLISHED' })
    api.listCourseModuleQuizzes.mockResolvedValue([])
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('DRAFT bank: submit new MCQ calls createQuestionBankQuestion with prompt, options, correct key', async () => {
    renderStudio()

    await waitFor(() => {
      expect(api.listCourseQuestionBanks).toHaveBeenCalledWith('c1')
      expect(api.listQuestionBankQuestions).toHaveBeenCalledWith('c1', 'qb1')
    })

    await screen.findByTestId('question-bank-studio-loaded')

    const prompt = await screen.findByTestId('studio-question-prompt')
    fireEvent.change(prompt, { target: { value: 'What is 2+2?' } })

    if (!screen.queryByTestId('studio-option-key-1')) {
      fireEvent.click(await screen.findByTestId('studio-add-option'))
    }

    fireEvent.change(await screen.findByTestId('studio-option-key-0'), { target: { value: 'a' } })
    fireEvent.change(await screen.findByTestId('studio-option-text-0'), { target: { value: 'Three' } })
    fireEvent.change(await screen.findByTestId('studio-option-key-1'), { target: { value: 'b' } })
    fireEvent.change(await screen.findByTestId('studio-option-text-1'), { target: { value: 'Four' } })

    const correctSelect = screen.getByTestId('studio-correct-select')
    fireEvent.change(correctSelect, { target: { value: 'b' } })

    fireEvent.click(screen.getByTestId('studio-add-question-submit'))

    await waitFor(() => {
      expect(api.createQuestionBankQuestion).toHaveBeenCalledWith(
        'c1',
        'qb1',
        expect.objectContaining({
          promptText: 'What is 2+2?',
          optionsJson: [
            { key: 'a', text: 'Three' },
            { key: 'b', text: 'Four' },
          ],
          correctOptionKey: 'b',
        }),
      )
    })
  })

  it('shows loaded marker after bank and questions list resolve', async () => {
    renderStudio()

    await waitFor(() => {
      expect(api.listQuestionBankQuestions).toHaveBeenCalledWith('c1', 'qb1')
    })

    expect(await screen.findByTestId('question-bank-studio-loaded')).toBeTruthy()
  })

  it('PUBLISHED bank: published question row has no Edit or Delete controls', async () => {
    api.listCourseQuestionBanks.mockResolvedValue([{ questionBankId: 'qb1', status: 'PUBLISHED' }])
    api.listQuestionBankQuestions.mockResolvedValue([
      {
        questionId: 'pub-q1',
        status: 'PUBLISHED',
        promptText: 'P?',
        optionsJson: [
          { key: 'a', text: 'A' },
          { key: 'b', text: 'B' },
        ],
        correctOptionKey: 'a',
      },
    ])

    renderStudio()

    await screen.findByTestId('question-bank-studio-loaded')

    expect(screen.queryByTestId('studio-question-edit-pub-q1')).toBeNull()
    expect(screen.queryByTestId('studio-question-delete-pub-q1')).toBeNull()

    const publishedBadges = screen.getAllByText('PUBLISHED')
    expect(publishedBadges.length).toBeGreaterThanOrEqual(1)
  })

  it('DRAFT edit: existing correct key cannot be cleared through the select', async () => {
    api.listQuestionBankQuestions.mockResolvedValue([
      {
        questionId: 'draft-q1',
        status: 'DRAFT',
        promptText: 'Draft?',
        optionsJson: [
          { key: 'a', text: 'A' },
          { key: 'b', text: 'B' },
        ],
        correctOptionKey: 'a',
      },
    ])

    renderStudio()

    await screen.findByTestId('question-bank-studio-loaded')
    fireEvent.click(screen.getByTestId('studio-question-edit-draft-q1'))

    const correctSelect = screen.getByLabelText('Correct key') as HTMLSelectElement
    const optionValues = Array.from(correctSelect.options).map((option) => option.value)
    expect(optionValues).toEqual(['a', 'b'])
    expect(optionValues).not.toContain('')
  })

  it('PUBLISHED bank: add question form is shown and submit sends correctOptionKey', async () => {
    api.listCourseQuestionBanks.mockResolvedValue([{ questionBankId: 'qb1', status: 'PUBLISHED' }])
    api.listQuestionBankQuestions.mockResolvedValue([])

    renderStudio()

    await screen.findByTestId('question-bank-studio-loaded')

    expect(screen.getByTestId('studio-add-question-submit')).toBeTruthy()

    const prompt = await screen.findByTestId('studio-question-prompt')
    fireEvent.change(prompt, { target: { value: 'New published-bank question' } })

    fireEvent.change(await screen.findByTestId('studio-option-key-0'), { target: { value: 'a' } })
    fireEvent.change(await screen.findByTestId('studio-option-text-0'), { target: { value: 'Alpha' } })
    fireEvent.change(await screen.findByTestId('studio-option-key-1'), { target: { value: 'b' } })
    fireEvent.change(await screen.findByTestId('studio-option-text-1'), { target: { value: 'Bravo' } })

    const correctSelect = screen.getByTestId('studio-correct-select')
    fireEvent.change(correctSelect, { target: { value: 'b' } })

    fireEvent.click(screen.getByTestId('studio-add-question-submit'))

    await waitFor(() => {
      expect(api.createQuestionBankQuestion).toHaveBeenCalledWith(
        'c1',
        'qb1',
        expect.objectContaining({
          promptText: 'New published-bank question',
          optionsJson: [
            { key: 'a', text: 'Alpha' },
            { key: 'b', text: 'Bravo' },
          ],
          correctOptionKey: 'b',
        }),
      )
    })
  })
})
