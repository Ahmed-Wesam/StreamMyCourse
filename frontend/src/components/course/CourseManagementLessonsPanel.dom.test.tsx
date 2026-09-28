/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Course, Lesson } from '../../lib/api/types'
import { CourseManagementLessonsPanel } from './CourseManagementLessonsPanel'

const course: Course = {
  id: 'c1',
  title: 'Course',
  description: '',
  status: 'DRAFT',
}

const lesson: Lesson = {
  id: 'l1',
  title: 'Intro',
  order: 1,
  moduleId: 'm1',
  moduleOrder: 0,
  videoStatus: 'ready',
}

afterEach(() => {
  cleanup()
})

describe('CourseManagementLessonsPanel attachments', () => {
  it('submits attach file with title, kind, and file input', async () => {
    const onAttach = vi.fn().mockResolvedValue(undefined)
    const file = new File(['bytes'], 'guide.pdf', { type: 'application/pdf' })

    render(
      <CourseManagementLessonsPanel
        course={course}
        sortedLessons={[lesson]}
        moduleTitleById={new Map([['m1', 'Module 1']])}
        lessonFilesByLessonId={{}}
        attachingLessonId={null}
        onAddLessonClick={() => undefined}
        onDeleteLesson={() => undefined}
        onAttachLessonFile={onAttach}
        onDeleteLessonFile={vi.fn()}
      />,
    )

    const form = screen.getByTestId('lesson-attach-form-l1')
    const formScope = within(form)
    fireEvent.change(formScope.getByLabelText('Title'), { target: { value: 'Study guide' } })
    fireEvent.change(formScope.getByLabelText('File kind'), { target: { value: 'download' } })
    const fileInput = formScope.getByLabelText('Attachment file') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })
    fireEvent.submit(form)

    await waitFor(() => {
      expect(onAttach).toHaveBeenCalledWith({
        lessonId: 'l1',
        title: 'Study guide',
        kind: 'download',
        file,
      })
    })
  })

  it('lists pending and ready files', () => {
    render(
      <CourseManagementLessonsPanel
        course={course}
        sortedLessons={[lesson]}
        moduleTitleById={new Map()}
        lessonFilesByLessonId={{
          l1: [
            {
              fileId: 'f1',
              title: 'Pending doc',
              kind: 'resource',
              fileType: 'pdf',
              byteSize: 10,
              status: 'pending',
            },
            {
              fileId: 'f2',
              title: 'Ready sheet',
              kind: 'download',
              fileType: 'csv',
              byteSize: 20,
              status: 'ready',
            },
          ],
        }}
        attachingLessonId={null}
        onAddLessonClick={() => undefined}
        onDeleteLesson={() => undefined}
        onAttachLessonFile={vi.fn()}
        onDeleteLessonFile={vi.fn()}
      />,
    )

    const list = screen.getByTestId('lesson-file-list-l1')
    expect(list.textContent).toMatch(/Pending doc/)
    expect(list.textContent).toMatch(/pending/i)
    expect(list.textContent).toMatch(/Ready sheet/)
  })
})
