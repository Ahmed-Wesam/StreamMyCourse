/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { SiteHeader, type SiteNavLink } from './SiteHeader'

const LINKS: SiteNavLink[] = [
  { href: '/courses', label: 'Courses' },
  { href: '/about', label: 'About' },
  { href: '/contact', label: 'Contact' },
]

function renderHeader(props: Partial<Parameters<typeof SiteHeader>[0]> = {}) {
  return render(
    <MemoryRouter>
      <SiteHeader links={LINKS} activePath="/" {...props} />
    </MemoryRouter>,
  )
}

describe('SiteHeader', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders links in order with correct hrefs in desktop and mobile nav', () => {
    renderHeader()

    const desktop = screen.getByRole('navigation', { name: 'Primary' })
    const desktopLinks = within(desktop).getAllByRole('link')
    expect(desktopLinks.map((el) => el.getAttribute('href'))).toEqual([
      '/courses',
      '/about',
      '/contact',
    ])
    expect(desktopLinks.map((el) => el.textContent)).toEqual(['Courses', 'About', 'Contact'])

    const mobile = screen.getByLabelText('Primary mobile')
    const mobileLinks = within(mobile).getAllByRole('link', { hidden: true })
    expect(mobileLinks.map((el) => el.getAttribute('href'))).toEqual([
      '/courses',
      '/about',
      '/contact',
    ])
  })

  it('marks the active link with aria-current="page"', () => {
    renderHeader({ activePath: '/about' })

    const desktop = screen.getByRole('navigation', { name: 'Primary' })
    const active = within(desktop).getByRole('link', { name: 'About' })
    expect(active.getAttribute('aria-current')).toBe('page')

    const courses = within(desktop).getByRole('link', { name: 'Courses' })
    expect(courses.getAttribute('aria-current')).toBeNull()
  })

  it('moves focus to the burger when a mobile link closes the menu', () => {
    renderHeader()
    const burger = screen.getByRole('button', { name: /menu/i })
    fireEvent.click(burger)

    const mobile = screen.getByLabelText('Primary mobile')
    const about = within(mobile).getByRole('link', { name: 'About' })
    about.focus()
    fireEvent.click(about)

    expect(mobile.getAttribute('aria-hidden')).toBe('true')
    expect(document.activeElement).toBe(burger)
  })

  it('burger toggles aria-expanded and mobile menu visibility', () => {
    renderHeader()

    const burger = screen.getByRole('button', { name: /menu/i })
    const mobile = screen.getByLabelText('Primary mobile')

    expect(burger.getAttribute('aria-expanded')).toBe('false')
    expect(mobile.getAttribute('aria-hidden')).toBe('true')

    fireEvent.click(burger)

    expect(burger.getAttribute('aria-expanded')).toBe('true')
    expect(mobile.getAttribute('aria-hidden')).toBe('false')

    fireEvent.click(burger)

    expect(burger.getAttribute('aria-expanded')).toBe('false')
    expect(mobile.getAttribute('aria-hidden')).toBe('true')
  })

  it('Escape closes the mobile menu', () => {
    renderHeader()

    const burger = screen.getByRole('button', { name: /menu/i })
    fireEvent.click(burger)
    expect(burger.getAttribute('aria-expanded')).toBe('true')

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(burger.getAttribute('aria-expanded')).toBe('false')
    expect(screen.getByLabelText('Primary mobile').getAttribute('aria-hidden')).toBe('true')
  })

  it('rerender with a different activePath closes the mobile menu', () => {
    const { rerender } = renderHeader()

    const burger = screen.getByRole('button', { name: /menu/i })
    fireEvent.click(burger)
    expect(burger.getAttribute('aria-expanded')).toBe('true')

    rerender(
      <MemoryRouter>
        <SiteHeader links={LINKS} activePath="/courses" />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: /menu/i }).getAttribute('aria-expanded')).toBe(
      'false',
    )
    expect(screen.getByLabelText('Primary mobile').getAttribute('aria-hidden')).toBe('true')
  })

  it('clicking a mobile nav link closes the menu', () => {
    renderHeader()

    const burger = screen.getByRole('button', { name: /menu/i })
    fireEvent.click(burger)

    const mobile = screen.getByRole('navigation', { name: 'Primary mobile' })
    fireEvent.click(within(mobile).getByRole('link', { name: 'Courses' }))

    expect(burger.getAttribute('aria-expanded')).toBe('false')
    expect(screen.getByLabelText('Primary mobile').getAttribute('aria-hidden')).toBe('true')
  })
})
