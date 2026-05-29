/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { Layout } from './Layout'

describe('Layout', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders chromeAlert between chromeHeader and main content', () => {
    render(
      <MemoryRouter>
        <Layout
          chromeHeader={<div data-testid="chrome-slot">Chrome</div>}
          chromeAlert={<div data-testid="alert-slot">Alert</div>}
        >
          <p>Body</p>
        </Layout>
      </MemoryRouter>,
    )

    const root = screen.getByText('Body').closest('.flex.min-h-screen')
    expect(root).toBeTruthy()
    const children = Array.from(root!.children)
    expect(children[0].getAttribute('data-testid')).toBe('chrome-slot')
    expect(children[1].getAttribute('data-testid')).toBe('alert-slot')
    expect(children[2].tagName).toBe('MAIN')
  })

  it('renders chromeHeader when provided', () => {
    render(
      <MemoryRouter>
        <Layout chromeHeader={<div data-testid="chrome-slot">Chrome</div>}>
          <p>Body</p>
        </Layout>
      </MemoryRouter>,
    )

    expect(screen.getByTestId('chrome-slot')).toBeTruthy()
    expect(screen.getByText('Body')).toBeTruthy()
  })

  it('does not force top padding when chromeHeader is set', () => {
    const { container } = render(
      <MemoryRouter>
        <Layout chromeHeader={<div data-testid="chrome">Nav</div>}>
          <span>Content</span>
        </Layout>
      </MemoryRouter>,
    )

    const mainInner = container.querySelector('main')?.firstElementChild
    expect(mainInner).toBeTruthy()
    expect(mainInner?.className).not.toMatch(/pt-/)
  })

  it('does not use pt-20 for main inner wrapper when chromeHeader is omitted', () => {
    const { container } = render(
      <MemoryRouter>
        <Layout>
          <span>Content</span>
        </Layout>
      </MemoryRouter>,
    )

    const mainInner = container.querySelector('main')?.firstElementChild
    expect(mainInner?.className).not.toMatch(/pt-20/)
    expect(mainInner?.className).toMatch(/pt-5/)
  })

  it('renders Footer consistently', () => {
    render(
      <MemoryRouter>
        <Layout>
          <p>Page</p>
        </Layout>
      </MemoryRouter>,
    )

    expect(screen.getByRole('contentinfo')).toBeTruthy()
    expect(screen.getByRole('link', { name: /Privacy/i }).getAttribute('href')).toBe('/privacy')
    expect(screen.getByRole('link', { name: /Terms/i }).getAttribute('href')).toBe('/terms')
  })

  it('renders Footer legal links as relative paths by default', () => {
    render(
      <MemoryRouter>
        <Layout>
          <p>Page</p>
        </Layout>
      </MemoryRouter>,
    )

    const privacy = screen.getByRole('link', { name: /Privacy/i })
    const terms = screen.getByRole('link', { name: /Terms/i })

    expect(privacy.tagName).toBe('A')
    expect(terms.tagName).toBe('A')
    expect(privacy.getAttribute('href')).toBe('/privacy')
    expect(terms.getAttribute('href')).toBe('/terms')
  })

  it('renders Footer legal links as absolute URLs when legalBaseUrl is set', () => {
    render(
      <MemoryRouter>
        <Layout legalBaseUrl="https://example-student.test">
          <p>Page</p>
        </Layout>
      </MemoryRouter>,
    )

    const privacy = screen.getByRole('link', { name: /Privacy/i })
    const terms = screen.getByRole('link', { name: /Terms/i })

    expect(privacy.tagName).toBe('A')
    expect(terms.tagName).toBe('A')
    expect(privacy.getAttribute('href')).toBe('https://example-student.test/privacy')
    expect(terms.getAttribute('href')).toBe('https://example-student.test/terms')
  })

  it('renders children inside main content area', () => {
    render(
      <MemoryRouter>
        <Layout chromeHeader={<div>Nav</div>}>
          <p data-testid="page-child">Unique child text</p>
        </Layout>
      </MemoryRouter>,
    )

    expect(screen.getByTestId('page-child')).toBeTruthy()
    expect(screen.getByText('Unique child text').closest('main')).toBeTruthy()
  })

  it('showChrome=false renders only children', () => {
    render(
      <MemoryRouter>
        <Layout showChrome={false}>
          <p data-testid="bare">Bare</p>
        </Layout>
      </MemoryRouter>,
    )

    expect(screen.getByTestId('bare')).toBeTruthy()
    expect(screen.queryByRole('contentinfo')).toBeNull()
  })
})
