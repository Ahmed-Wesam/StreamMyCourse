/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import TeacherAssignmentsPage from './TeacherAssignmentsPage'

const api = vi.hoisted(() => ({
  createAssignment: vi.fn(),
  patchAssignment: vi.fn(),
  createAssignmentImageUpload: vi.fn(),
  putAssignmentUpload: vi.fn(),
  completeAssignmentImageUpload: vi.fn(),
  listCourseModules: vi.fn(),
}))

vi.mock('../../lib/api/assignments', () => ({
  createAssignment: (...args: unknown[]) => api.createAssignment(...args),
  patchAssignment: (...args: unknown[]) => api.patchAssignment(...args),
  createAssignmentImageUpload: (...args: unknown[]) => api.createAssignmentImageUpload(...args),
  putAssignmentUpload: (...args: unknown[]) => api.putAssignmentUpload(...args),
  completeAssignmentImageUpload: (...args: unknown[]) =>
    api.completeAssignmentImageUpload(...args),
}))

vi.mock('../../lib/api/catalog', () => ({
  listCourseModules: (...args: unknown[]) => api.listCourseModules(...args),
}))

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  api.createAssignment.mockReset()
  api.patchAssignment.mockReset()
  api.createAssignmentImageUpload.mockReset()
  api.putAssignmentUpload.mockReset()
  api.completeAssignmentImageUpload.mockReset()
  api.listCourseModules.mockReset()

  api.listCourseModules.mockResolvedValue([{ id: 'm1', title: 'Module 1', sortOrder: 1 }])
  api.createAssignment.mockResolvedValue({
    id: 'a1',
    title: 'Lab write-up',
    moduleId: 'm1',
    status: 'draft',
    passPercent: 70,
    countsTowardCertificate: false,
    locked: false,
    instructions: { mode: 'plain', text: '' },
    rubric: { mode: 'plain', text: '' },
    criteria: [],
    myLatest: null,
  })
  api.patchAssignment.mockResolvedValue({
    id: 'a1',
    title: 'Lab write-up',
    moduleId: 'm1',
    status: 'published',
    passPercent: 70,
    countsTowardCertificate: false,
    locked: false,
    instructions: { mode: 'plain', text: 'Do the lab.' },
    rubric: { mode: 'plain', text: '' },
    criteria: [{ id: 'c1', label: 'Clarity', maxPoints: 10 }],
    myLatest: null,
  })
  api.createAssignmentImageUpload.mockResolvedValue({
    uploadUrl: 'https://upload.example/presigned',
  })
  api.putAssignmentUpload.mockResolvedValue(undefined)
  api.completeAssignmentImageUpload.mockResolvedValue({ slot: 'instructions', status: 'ready' })
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/courses/c1/assignments']}>
      <Routes>
        <Route path="/courses/:courseId/assignments" element={<TeacherAssignmentsPage />} />
        <Route
          path="/courses/:courseId/assignments/:assignmentId/review"
          element={<div data-testid="review-page">Review</div>}
        />
      </Routes>
    </MemoryRouter>,
  )
}

async function fillCommonFields() {
  await waitFor(() => {
    expect(screen.getByLabelText(/Module/i)).toBeTruthy()
  })
  fireEvent.change(screen.getByLabelText(/^Title$/i), { target: { value: 'Lab write-up' } })
  fireEvent.change(screen.getByLabelText(/^Label$/i), { target: { value: 'Clarity' } })
}

describe('TeacherAssignmentsPage', () => {
  it('publishes plain text via create without instructions, then patch with instructions/criteria/status', async () => {
    renderPage()
    await fillCommonFields()

    fireEvent.change(screen.getByLabelText(/Instructions mode/i), { target: { value: 'plain' } })
    fireEvent.change(screen.getByLabelText(/^Instructions$/i), {
      target: { value: 'Do the lab.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Publish assignment/i }))

    await waitFor(() => {
      expect(api.createAssignment).toHaveBeenCalledTimes(1)
    })

    expect(api.createAssignment).toHaveBeenCalledWith('c1', {
      title: 'Lab write-up',
      moduleId: 'm1',
      passPercent: 70,
      countsTowardCertificate: false,
    })
    expect(api.createAssignment.mock.calls[0][1]).not.toHaveProperty('instructions')
    expect(api.createAssignment.mock.calls[0][1]).not.toHaveProperty('criteria')
    expect(api.createAssignment.mock.calls[0][1]).not.toHaveProperty('rubric')

    await waitFor(() => {
      expect(api.patchAssignment).toHaveBeenCalledWith('c1', 'a1', {
        instructions: { mode: 'plain', text: 'Do the lab.' },
        criteria: [{ label: 'Clarity', maxPoints: 10 }],
        status: 'published',
      })
    })
  })

  it('publishes image instructions via upload then status published without the plain/rich error', async () => {
    renderPage()
    await fillCommonFields()

    fireEvent.change(screen.getByLabelText(/Instructions mode/i), { target: { value: 'image' } })

    const fileInput = await waitFor(() => {
      const input = document.querySelector('input[type="file"]') as HTMLInputElement | null
      expect(input).toBeTruthy()
      return input!
    })
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'sheet.png', { type: 'image/png' })
    fireEvent.change(fileInput, { target: { files: [file] } })

    fireEvent.click(screen.getByRole('button', { name: /Publish assignment/i }))

    await waitFor(() => {
      expect(api.createAssignment).toHaveBeenCalledWith('c1', {
        title: 'Lab write-up',
        moduleId: 'm1',
        passPercent: 70,
        countsTowardCertificate: false,
      })
    })

    await waitFor(() => {
      expect(api.patchAssignment).toHaveBeenCalledWith('c1', 'a1', {
        criteria: [{ label: 'Clarity', maxPoints: 10 }],
      })
    })

    await waitFor(() => {
      expect(api.createAssignmentImageUpload).toHaveBeenCalledWith('c1', 'a1', {
        slot: 'instructions',
        contentType: 'image/png',
        byteSize: file.size,
      })
    })
    expect(api.putAssignmentUpload).toHaveBeenCalledWith(
      'https://upload.example/presigned',
      file,
      'image/png',
    )
    expect(api.completeAssignmentImageUpload).toHaveBeenCalledWith('c1', 'a1', 'instructions')

    await waitFor(() => {
      expect(api.patchAssignment).toHaveBeenCalledWith('c1', 'a1', { status: 'published' })
    })

    expect(
      screen.queryByText(/Publish with plain or rich instructions first/i),
    ).toBeNull()
    expect(screen.queryByText(/Use plain or rich text to publish/i)).toBeNull()
  })
})
