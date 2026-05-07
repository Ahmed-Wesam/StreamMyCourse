/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import type { Course } from '../../lib/api'
import { CourseCard } from './CourseCard'

function renderCard(course: Course) {
  return render(
    <MemoryRouter>
      <CourseCard course={course} />
    </MemoryRouter>,
  )
}

describe('CourseCard', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders thumbnail image when course has thumbnailUrl', () => {
    renderCard({
      id: 'c1',
      title: 'Algebra',
      description: 'Numbers',
      status: 'PUBLISHED',
      thumbnailUrl: 'https://cdn.example/thumb.jpg',
    })
    const img = document.querySelector('img[src="https://cdn.example/thumb.jpg"]')
    expect(img).not.toBeNull()
  })

  it('renders placeholder when course has no thumbnailUrl', () => {
    renderCard({
      id: 'c2',
      title: 'Geometry',
      description: 'Shapes',
      status: 'PUBLISHED',
    })
    expect(document.querySelector('img')).toBeNull()
    expect(screen.getByRole('link', { name: /Geometry/i })).toBeTruthy()
  })

  it('shows default description copy when description is empty', () => {
    renderCard({
      id: 'c3',
      title: 'Trig',
      description: '',
      status: 'PUBLISHED',
    })
    expect(screen.getByText(/Explore this course on Stream My Course/i)).toBeTruthy()
  })
})
