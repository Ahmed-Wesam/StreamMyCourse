/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { StudentDashboardStatsRow } from './StudentDashboardStatsRow'

afterEach(() => {
  cleanup()
})

describe('StudentDashboardStatsRow certificates', () => {
  it('shows non-revoked certificate count and links to /certificates', () => {
    render(
      <MemoryRouter>
        <StudentDashboardStatsRow
          stats={{
            availability: 'ready',
            activeCourses: 2,
            overallProgressPercent: 50,
            quizzesPassed: { passed: 1, visible: 2 },
          }}
          certificatesCount={3}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('Certificates')).toBeTruthy()
    expect(screen.getByText('3')).toBeTruthy()
    const link = screen.getByRole('link', { name: /Certificates/i })
    expect(link.getAttribute('href')).toBe('/certificates')
  })

  it('shows 0 when certificatesCount is zero', () => {
    render(
      <MemoryRouter>
        <StudentDashboardStatsRow
          stats={{
            availability: 'ready',
            activeCourses: 1,
            overallProgressPercent: 10,
            quizzesPassed: { passed: 0, visible: 1 },
          }}
          certificatesCount={0}
        />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: /Certificates/i })
    expect(link.textContent).toMatch(/0/)
  })

  it('shows em dash when certificates are unavailable', () => {
    render(
      <MemoryRouter>
        <StudentDashboardStatsRow
          stats={{
            availability: 'unavailable',
            activeCourses: 0,
            overallProgressPercent: null,
            quizzesPassed: null,
          }}
          certificatesCount={null}
        />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: /Certificates/i })
    expect(link.getAttribute('href')).toBe('/certificates')
    expect(link.textContent).toMatch(/—/)
  })
})
