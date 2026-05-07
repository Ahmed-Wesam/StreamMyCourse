/**
 * @vitest-environment jsdom
 */
import type { ChangeEvent } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Course } from '../../lib/api'
import { CourseThumbnailEditor } from './CourseThumbnailEditor'

const baseCourse: Course = {
  id: 'c1',
  title: 'T',
  description: 'D',
  status: 'DRAFT',
}

function renderEditor(
  overrides: Partial<{
    course: Course
    thumbFile: File | null
    thumbUploading: boolean
    onThumbFileChange: (e: ChangeEvent<HTMLInputElement>) => void
    onUpload: () => void
  }> = {},
) {
  const onThumbFileChange = overrides.onThumbFileChange ?? vi.fn()
  const onUpload = overrides.onUpload ?? vi.fn()
  return render(
    <CourseThumbnailEditor
      course={overrides.course ?? baseCourse}
      thumbFile={overrides.thumbFile ?? null}
      thumbUploading={overrides.thumbUploading ?? false}
      onThumbFileChange={onThumbFileChange}
      onUpload={onUpload}
    />,
  )
}

describe('CourseThumbnailEditor', () => {
  afterEach(() => {
    cleanup()
  })

  it('shows placeholder when course has no thumbnailUrl', () => {
    renderEditor()
    expect(screen.getByText('No thumbnail')).toBeTruthy()
    expect(document.querySelector('img')).toBeNull()
  })

  it('shows current thumbnail image when course has thumbnailUrl', () => {
    renderEditor({
      course: { ...baseCourse, thumbnailUrl: 'https://cdn.example/t.jpg' },
    })
    const img = document.querySelector('img')
    expect(img?.getAttribute('src')).toBe('https://cdn.example/t.jpg')
  })

  it('shows selected file name and size when thumbFile is set', () => {
    const file = new File([new Uint8Array(2048)], 'hero.png', { type: 'image/png' })
    renderEditor({ thumbFile: file })
    expect(screen.getByText(/Selected: hero.png/i)).toBeTruthy()
    expect(screen.getByText(/\(2 KB\)/)).toBeTruthy()
  })

  it('disables upload when no file is chosen', () => {
    renderEditor()
    expect(screen.getByRole('button', { name: 'Upload thumbnail' }).hasAttribute('disabled')).toBe(true)
  })

  it('disables upload while uploading', () => {
    const file = new File([], 'a.jpg', { type: 'image/jpeg' })
    renderEditor({ thumbFile: file, thumbUploading: true })
    expect(screen.getByRole('button', { name: 'Uploading…' }).hasAttribute('disabled')).toBe(true)
  })

  it('calls onUpload when enabled button is clicked', () => {
    const onUpload = vi.fn()
    const file = new File([], 'a.jpg', { type: 'image/jpeg' })
    renderEditor({ thumbFile: file, onUpload })
    fireEvent.click(screen.getByRole('button', { name: 'Upload thumbnail' }))
    expect(onUpload).toHaveBeenCalledTimes(1)
  })

  it('forwards file input changes to onThumbFileChange', () => {
    const onThumbFileChange = vi.fn()
    renderEditor({ onThumbFileChange })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([], 'picked.webp', { type: 'image/webp' })
    fireEvent.change(input, { target: { files: [file] } })
    expect(onThumbFileChange).toHaveBeenCalledTimes(1)
  })
})
