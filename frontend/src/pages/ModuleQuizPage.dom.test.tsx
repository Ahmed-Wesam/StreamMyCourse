/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ModuleQuizPage from './ModuleQuizPage'

const api = vi.hoisted(() => ({
  startModuleQuiz: vi.fn(),
}))

vi.mock('../lib/api', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api')
  return {
    ...mod,
    startModuleQuiz: (...args: unknown[]) =>
      api.startModuleQuiz(...args) as ReturnType<typeof mod.startModuleQuiz>,
  }
})

/** API order reversed vs naive binding order q1 → q2; options shuffled per question. */
const REVERSED_START_RESPONSE = {
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

function renderModuleQuiz(path = '/courses/c1/modules/m1/quiz') {
  return render(
    <MemoryRouter initialEntries={[path]}>
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
    api.startModuleQuiz.mockResolvedValue(REVERSED_START_RESPONSE)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
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

    const fieldsets = screen.getAllByRole('group')
    expect(fieldsets).toHaveLength(2)

    expect(within(fieldsets[0]!).getByText('Capital of France?')).toBeTruthy()
    expect(within(fieldsets[1]!).getByText('What is 2 + 2?')).toBeTruthy()

    expect(optionKeysInFieldset(fieldsets[0]!)).toEqual(['B', 'A'])
    expect(optionLabelsInFieldset(fieldsets[0]!)).toEqual(['Paris', 'Berlin'])

    expect(optionKeysInFieldset(fieldsets[1]!)).toEqual(['B', 'A'])
    expect(optionLabelsInFieldset(fieldsets[1]!)).toEqual(['4', '3'])
  })

  it('does not render a Submit button', async () => {
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('Capital of France?')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /submit/i })).toBeNull()
  })
})
