/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import QuestionBanksListPage from './QuestionBanksListPage'

const FORBIDDEN_CLASS_SUBSTRINGS = [
  'emerald-',
  'blue-600',
  'green-',
  'gray-',
  'slate-',
  'amber-',
] as const

function collectClassNames(root: Element): string[] {
  const names: string[] = []
  const walk = (el: Element) => {
    if (typeof el.className === 'string' && el.className.length > 0) {
      names.push(el.className)
    }
    for (const child of el.children) {
      walk(child)
    }
  }
  walk(root)
  return names
}

function findForbiddenPaletteClasses(classNames: string[]): string[] {
  const hits: string[] = []
  for (const cn of classNames) {
    for (const forbidden of FORBIDDEN_CLASS_SUBSTRINGS) {
      if (cn.includes(forbidden)) {
        hits.push(`${forbidden} → ${cn}`)
      }
    }
  }
  return hits
}

function expectRsPaletteOnRoot(root: Element | null) {
  expect(root).toBeTruthy()
  expect(root!.className).toMatch(/text-rs-ink/)
  const violations = findForbiddenPaletteClasses(collectClassNames(root!))
  expect(violations).toEqual([])
}

const api = vi.hoisted(() => ({
  listCourseQuestionBanks: vi.fn(),
  createQuestionBank: vi.fn(),
}))

const mockNavigate = vi.fn()
const mockRouteParams = vi.hoisted(() => ({ courseId: 'c1' }))

vi.mock('react-router-dom', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('react-router-dom')
  return {
    ...mod,
    useNavigate: () => mockNavigate,
    useParams: () => mockRouteParams,
  }
})

vi.mock('../lib/api/questionBanks', async (importOriginal) => {
  const mod = (await importOriginal()) as typeof import('../lib/api/questionBanks')
  return {
    ...mod,
    listCourseQuestionBanks: (...args: unknown[]) =>
      api.listCourseQuestionBanks(...args) as ReturnType<typeof mod.listCourseQuestionBanks>,
    createQuestionBank: (...args: unknown[]) =>
      api.createQuestionBank(...args) as ReturnType<typeof mod.createQuestionBank>,
  }
})

function renderQuestionBanksList(initialEntries: string[] = ['/courses/c1/question-banks']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/courses/:courseId/question-banks" element={<QuestionBanksListPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('QuestionBanksListPage', () => {
  beforeEach(() => {
    api.listCourseQuestionBanks.mockReset()
    api.createQuestionBank.mockReset()
    mockNavigate.mockReset()
    mockRouteParams.courseId = 'c1'

    api.listCourseQuestionBanks.mockResolvedValue([
      { questionBankId: 'qb-a', name: 'Midterm bank', status: 'DRAFT' },
      { questionBankId: 'qb-b', name: 'Final review', status: 'PUBLISHED' },
    ])
    api.createQuestionBank.mockResolvedValue({ questionBankId: 'qb-new', name: 'Chapter 1 quiz' })
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('loads and shows a row per bank with name as the primary label', async () => {
    renderQuestionBanksList()

    await waitFor(() => {
      expect(api.listCourseQuestionBanks).toHaveBeenCalledWith('c1')
    })

    expect(screen.getByText('Midterm bank')).toBeTruthy()
    expect(screen.getByText('Final review')).toBeTruthy()
    expect(screen.queryByText('ID: qb-a')).toBeNull()
    expect(screen.queryByText('qb-a')).toBeNull()
    expect(screen.getByText('Draft')).toBeTruthy()
    expect(screen.getByText('Published')).toBeTruthy()
  })

  it('create control collects a name, calls API, then navigates to the new bank route', async () => {
    renderQuestionBanksList()

    const nameInput = await waitFor(() => screen.getByLabelText(/^New bank name$/i))
    fireEvent.change(nameInput, { target: { value: 'Chapter 1 quiz' } })
    const createBtn = await waitFor(() => screen.getByTestId('question-banks-create'))
    fireEvent.click(createBtn)

    await waitFor(() => {
      expect(api.createQuestionBank).toHaveBeenCalledWith('c1', { name: 'Chapter 1 quiz' })
    })
    expect(mockNavigate).toHaveBeenCalledWith('/courses/c1/question-banks/qb-new')
  })

  it('uses RS palette on settled question banks list (no legacy Tailwind color utilities)', async () => {
    const { container } = renderQuestionBanksList()

    await screen.findByText('Midterm bank')
    expect(document.querySelector('.animate-pulse')).toBeNull()

    expectRsPaletteOnRoot(container.firstElementChild)
  })
})
