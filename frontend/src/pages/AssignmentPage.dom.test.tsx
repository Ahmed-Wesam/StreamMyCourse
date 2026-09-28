/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SafeRichText } from '../components/assignments/SafeRichText'
import AssignmentPage from './AssignmentPage'

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
  it('hides the upload form when the assignment is locked', async () => {
    api.getAssignment.mockResolvedValue({
      ...unlockedAssignment,
      locked: true,
    })

    renderAssignmentPage()

    await waitFor(() => {
      expect(screen.getByText(/Final write-up/)).toBeTruthy()
    })

    expect(screen.queryByLabelText(/upload file/i)).toBeNull()
    expect(screen.queryByRole('button', { name: /submit/i })).toBeNull()
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
