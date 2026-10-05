/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const listPublishedCourses = vi.fn()

vi.mock('../lib/api/public-catalog', () => ({
  listPublishedCourses: (...args: unknown[]) => listPublishedCourses(...args),
}))

import HomePage from './HomePage'

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )
}

describe('HomePage', () => {
  beforeEach(() => {
    listPublishedCourses.mockReset()
    listPublishedCourses.mockResolvedValue([
      { id: 'method-1', title: 'Research Methodology', description: 'Live description' },
      { id: 'stats-1', title: 'Statistics & SPSS', description: 'Live stats' },
      { id: 'write-1', title: 'Scientific Writing', description: 'Live writing' },
      { id: 'srma-1', title: 'Systematic Reviews & Meta-Analysis', description: 'Live reviews' },
    ])
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the prototype research-team timeline and eligibility copy', async () => {
    renderHome()

    expect(
      await screen.findByRole('heading', { name: 'Interview & Selection Process' }),
    ).toBeTruthy()
    expect(
      screen.getByText('Selected applicants move through interviews and a structured review.'),
    ).toBeTruthy()
    expect(
      screen.getByText(
        'Students who complete all four courses become eligible to apply for the Research Spectrum Research Team.',
      ),
    ).toBeTruthy()
    expect(
      screen.getByText(
        'Selection is based on interviews, course performance, assignments, English proficiency, and research skills.',
      ),
    ).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Selection & Review' })).toBeNull()
    expect(screen.queryByRole('link', { name: /^Learn more$/ })).toBeNull()
  })

  it('renders static prototype course cards, prices, and bundle enrollment', async () => {
    renderHome()

    expect(await screen.findByText('Formulate research questions')).toBeTruthy()
    expect(screen.getByText('Design robust studies')).toBeTruthy()
    expect(screen.getByText('Run ANOVA, Chi-Square, Regression & Logistic Regression')).toBeTruthy()
    expect(screen.getByText('Perform Survival Analysis in SPSS')).toBeTruthy()
    expect(screen.getByText('Structure scientific manuscripts')).toBeTruthy()
    expect(screen.getByText('Conduct systematic searches')).toBeTruthy()
    expect(screen.getByText('Save $50 vs. buying separately')).toBeTruthy()
    expect(screen.getAllByText('one-time payment').length).toBe(5)
    expect(screen.queryByText('Courses will appear here')).toBeNull()
    expect(screen.queryByText('Live description')).toBeNull()
    expect(screen.queryByText('$49.00')).toBeNull()
    expect(screen.queryByText('$150.00')).toBeNull()

    const prices = document.querySelectorAll('.pg-home .course-card .price')
    expect(prices).toHaveLength(4)
    for (const price of prices) {
      expect(price.textContent?.replace(/\s+/g, ' ').trim()).toBe('$50 one-time payment')
    }
    expect(document.querySelector('.pg-home .bundle .bprice span')?.textContent).toBe('$150')
    expect(document.querySelector('.pg-home .bundle .bprice small')?.textContent).toBe('one-time payment')

    await waitFor(() => {
      expect(
        screen.getAllByRole('link', { name: /^View Course$/i }).map((link) => link.getAttribute('href')),
      ).toEqual(['/courses/method-1', '/courses/stats-1', '/courses/write-1', '/courses/srma-1'])
    })

    expect(screen.getByRole('link', { name: /Enroll in Bundle/i }).getAttribute('href')).toBe(
      '/checkout?productType=bundle',
    )

    const explore = screen.getAllByRole('link', { name: /^Explore Courses$/i })
    expect(explore.length).toBeGreaterThan(0)
    for (const link of explore) {
      expect(link.getAttribute('href')).toBe('/courses#courses-catalog')
    }

    const learnMore = screen.getAllByRole('link', { name: /^Learn More$/i })
    expect(learnMore.length).toBeGreaterThan(0)
    for (const link of learnMore) {
      expect(link.getAttribute('href')).toBe('#courses')
    }

    expect(screen.getByRole('link', { name: /View All FAQs/i }).getAttribute('href')).toBe('/faq')
  })

  it('uses prototype section classes and omits the demo widget', async () => {
    renderHome()

    expect(await screen.findByText('Formulate research questions')).toBeTruthy()
    const root = document.querySelector('.pg-home')
    expect(root).toBeTruthy()
    expect(root?.getAttribute('data-testid')).toBe('student-page-home')
    expect(root?.querySelector('.hero')).toBeTruthy()
    expect(root?.querySelector('.hero-visual .books')).toBeTruthy()
    expect(root?.querySelector('.trust-card')).toBeTruthy()
    expect(root?.querySelectorAll('.out-card').length).toBe(5)
    expect(root?.querySelector('.journey .road')).toBeTruthy()
    expect(root?.querySelectorAll('.course-card').length).toBe(4)
    expect(root?.querySelector('.bundle')).toBeTruthy()
    expect(root?.querySelector('.beyond .timeline')).toBeTruthy()
    expect(root?.querySelectorAll('.who-grid .feat').length).toBe(5)
    expect(root?.querySelectorAll('.faq-item').length).toBe(4)
    expect(root?.querySelector('.cta-inner')).toBeTruthy()
    expect(root?.querySelector('#rs-dev-widget')).toBeNull()
    expect(screen.queryByText(/Demo State/i)).toBeNull()
    expect(document.getElementById('courses')).toBeTruthy()
  })
})
