/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
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

function renderModuleQuiz(path = '/courses/c1/modules/m1/quiz') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/courses/:courseId/modules/:moduleId/quiz" element={<ModuleQuizPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ModuleQuizPage', () => {
  beforeEach(() => {
    api.startModuleQuiz.mockReset()
    api.startModuleQuiz.mockResolvedValue({
      moduleQuizId: 'mq1',
      moduleId: 'm1',
      servedCountN: 2,
      questions: [
        {
          id: 'q1',
          promptText: 'What is 2 + 2?',
          optionsJson: [
            { key: 'A', text: '3' },
            { key: 'B', text: '4' },
          ],
        },
        {
          id: 'q2',
          promptText: 'Capital of France?',
          optionsJson: [
            { key: 'A', text: 'Berlin' },
            { key: 'B', text: 'Paris' },
          ],
        },
      ],
    })
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

  it('renders question prompts and options from start response', async () => {
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('What is 2 + 2?')).toBeTruthy()
    })
    expect(screen.getByText('Capital of France?')).toBeTruthy()
    expect(screen.getByLabelText('3')).toBeTruthy()
    expect(screen.getByLabelText('4')).toBeTruthy()
    expect(screen.getByLabelText('Paris')).toBeTruthy()
  })

  it('does not render a Submit button', async () => {
    renderModuleQuiz()

    await waitFor(() => {
      expect(screen.getByText('What is 2 + 2?')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /submit/i })).toBeNull()
  })
})
