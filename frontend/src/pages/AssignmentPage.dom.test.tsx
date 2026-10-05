/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SafeRichText } from '../components/assignments/SafeRichText'
import AssignmentPage from './AssignmentPage'

vi.mock('../lib/api/catalog', () => ({
  getCourse: vi.fn().mockResolvedValue({ id: 'c1', title: 'Research Methodology', status: 'PUBLISHED' }),
}))

const api = vi.hoisted(() => ({
  getAssignment: vi.fn(),
  getAssignmentImageUrl: vi.fn(),
  createAssignmentSubmission: vi.fn(),
  createAssignmentSubmissionFile: vi.fn(),
  completeAssignmentSubmissionFile: vi.fn(),
  submitAssignmentSubmission: vi.fn(),
  putAssignmentUpload: vi.fn(),
}))

vi.mock('../lib/api/assignments', () => ({
  getAssignment: (...args: unknown[]) => api.getAssignment(...args),
  getAssignmentImageUrl: (...args: unknown[]) => api.getAssignmentImageUrl(...args),
  createAssignmentSubmission: (...args: unknown[]) => api.createAssignmentSubmission(...args),
  createAssignmentSubmissionFile: (...args: unknown[]) => api.createAssignmentSubmissionFile(...args),
  completeAssignmentSubmissionFile: (...args: unknown[]) =>
    api.completeAssignmentSubmissionFile(...args),
  submitAssignmentSubmission: (...args: unknown[]) => api.submitAssignmentSubmission(...args),
  putAssignmentUpload: (...args: unknown[]) => api.putAssignmentUpload(...args),
}))

const unlockedAssignment = {
  id: 'a1',
  title: 'Final write-up',
  moduleId: 'm1',
  status: 'published' as const,
  passPercent: 70,
  countsTowardCertificate: true,
  locked: false,
  instructions: { mode: 'plain' as const, text: 'Upload your analysis.' },
  rubric: { mode: 'plain' as const, text: 'Clarity matters.' },
  criteria: [{ id: 'c1', label: 'Clarity', maxPoints: 10 }],
  myLatest: null,
}

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  api.getAssignment.mockReset()
  api.getAssignmentImageUrl.mockReset()
  api.createAssignmentSubmission.mockReset()
  api.createAssignmentSubmissionFile.mockReset()
  api.completeAssignmentSubmissionFile.mockReset()
  api.submitAssignmentSubmission.mockReset()
  api.putAssignmentUpload.mockReset()
  api.getAssignment.mockResolvedValue(unlockedAssignment)
})

function renderAssignmentPage() {
  return render(
    <MemoryRouter initialEntries={['/courses/c1/assignments/a1']}>
      <Routes>
        <Route path="/courses/:courseId/assignments/:assignmentId" element={<AssignmentPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('SafeRichText', () => {
  it('does not create a script element from markup that includes a script tag', () => {
    const { container } = render(
      <SafeRichText html="<p>ok</p><script>alert(1)</script>" />,
    )
    expect(container.querySelector('script')).toBeNull()
    expect(container.textContent).toMatch(/ok/)
  })
})

describe('AssignmentPage', () => {
  it('renders the pg-assignment prototype shell', async () => {
    renderAssignmentPage()

    await waitFor(() => {
      expect(screen.getByTestId('assignment-page')).toBeTruthy()
    })
    expect(document.querySelector('.pg-assignment')).toBeTruthy()
  })

  it('shows key prototype section headings', async () => {
    renderAssignmentPage()

    await waitFor(() => {
      expect(screen.getByText('Assignment Overview')).toBeTruthy()
    })
    expect(screen.getByText(/Certificate Readiness/i)).toBeTruthy()
    expect(screen.getByText(/Before You Submit/i)).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Assignment Submission/i })).toBeTruthy()
    expect(screen.getByText('Submission Portal')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1, name: /Final Assignment/i })).toBeTruthy()
  })

  it('submits a file through the mocked assignment API', async () => {
    api.createAssignmentSubmission.mockResolvedValue({ id: 'sub-1' })
    api.createAssignmentSubmissionFile.mockResolvedValue({
      fileId: 'f1',
      uploadUrl: 'https://upload.example/put',
    })
    api.putAssignmentUpload.mockResolvedValue(undefined)
    api.completeAssignmentSubmissionFile.mockResolvedValue(undefined)
    api.submitAssignmentSubmission.mockResolvedValue(undefined)
    api.getAssignment
      .mockResolvedValueOnce(unlockedAssignment)
      .mockResolvedValueOnce({
        ...unlockedAssignment,
        myLatest: { id: 'sub-1', status: 'submitted' },
      })

    renderAssignmentPage()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Final write-up' })).toBeTruthy()
    })

    const file = new File(['hello'], 'proposal.pdf', { type: 'application/pdf' })
    const input = screen.getByLabelText(/upload primary file/i)
    fireEvent.change(input, { target: { files: [file] } })

    fireEvent.click(screen.getByRole('button', { name: /submit assignment/i }))
    fireEvent.click(screen.getByRole('button', { name: /confirm submission/i }))

    await waitFor(() => {
      expect(api.createAssignmentSubmission).toHaveBeenCalledWith('c1', 'a1')
    })
    expect(api.submitAssignmentSubmission).toHaveBeenCalledWith('c1', 'a1', 'sub-1', {})
  })

  it('hides the upload form when the assignment is locked', async () => {
    api.getAssignment.mockResolvedValue({
      ...unlockedAssignment,
      locked: true,
    })

    renderAssignmentPage()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Final write-up' })).toBeTruthy()
    })

    expect(screen.queryByLabelText(/upload primary file/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /^Submit Assignment$/i })).toBeNull()
    expect(screen.getByText(/earlier module quizzes must be passed/i)).toBeTruthy()
  })

  it('renders graded feedback as plain text, not HTML markup', async () => {
    api.getAssignment.mockResolvedValue({
      ...unlockedAssignment,
      myLatest: {
        id: 's1',
        status: 'graded',
        scorePercent: 80,
        passed: true,
        feedback: 'Looks <b>good</b>',
      },
    })

    renderAssignmentPage()

    await waitFor(() => {
      expect(screen.getByText('Looks <b>good</b>')).toBeTruthy()
    })
    expect(screen.queryByRole('strong')).toBeNull()
    const feedback = screen.getByTestId('assignment-feedback')
    expect(feedback.querySelector('b')).toBeNull()
  })
})
