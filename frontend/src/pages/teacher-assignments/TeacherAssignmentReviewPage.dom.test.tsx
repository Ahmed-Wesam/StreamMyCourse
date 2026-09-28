/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import TeacherAssignmentReviewPage from './TeacherAssignmentReviewPage'

const api = vi.hoisted(() => ({
  getAssignment: vi.fn(),
  listAssignmentSubmissions: vi.fn(),
  gradeAssignmentSubmission: vi.fn(),
}))

vi.mock('../../lib/api/assignments', () => ({
  getAssignment: (...args: unknown[]) => api.getAssignment(...args),
  listAssignmentSubmissions: (...args: unknown[]) => api.listAssignmentSubmissions(...args),
  gradeAssignmentSubmission: (...args: unknown[]) => api.gradeAssignmentSubmission(...args),
}))

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  api.getAssignment.mockReset()
  api.listAssignmentSubmissions.mockReset()
  api.gradeAssignmentSubmission.mockReset()
  api.getAssignment.mockResolvedValue({
    id: 'a1',
    title: 'Lab report',
    moduleId: 'm1',
    status: 'published',
    passPercent: 70,
    countsTowardCertificate: false,
    locked: false,
    instructions: { mode: 'plain', text: 'Do the lab.' },
    rubric: { mode: 'plain', text: '' },
    criteria: [
      { id: 'c1', label: 'Method', maxPoints: 10 },
      { id: 'c2', label: 'Results', maxPoints: 10 },
    ],
    myLatest: null,
  })
  api.listAssignmentSubmissions.mockResolvedValue([
    {
      id: 'sub1',
      status: 'submitted',
      note: 'Please review',
    },
  ])
  api.gradeAssignmentSubmission.mockResolvedValue({ scorePercent: 80, passed: true })
})

function renderReview() {
  return render(
    <MemoryRouter initialEntries={['/courses/c1/assignments/a1/review']}>
      <Routes>
        <Route
          path="/courses/:courseId/assignments/:assignmentId/review"
          element={<TeacherAssignmentReviewPage />}
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TeacherAssignmentReviewPage', () => {
  it('sends criterion scores and feedback through the mocked grade client', async () => {
    renderReview()

    await waitFor(() => {
      expect(screen.getByText(/Lab report/)).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: /grade submission/i }))

    await waitFor(() => {
      expect(screen.getByLabelText(/Method/i)).toBeTruthy()
    })

    fireEvent.change(screen.getByLabelText(/Method/i), { target: { value: '8' } })
    fireEvent.change(screen.getByLabelText(/Results/i), { target: { value: '8' } })
    fireEvent.change(screen.getByLabelText(/Feedback/i), {
      target: { value: 'Solid work overall.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /submit grade/i }))

    await waitFor(() => {
      expect(api.gradeAssignmentSubmission).toHaveBeenCalledWith('c1', 'a1', 'sub1', {
        scores: [
          { criterionId: 'c1', points: 8 },
          { criterionId: 'c2', points: 8 },
        ],
        feedback: 'Solid work overall.',
      })
    })
  })
})
