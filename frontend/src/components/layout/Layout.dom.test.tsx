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

  it('applies pt-20 top padding on main inner wrapper when chromeHeader is set', () => {
    const { container } = render(
      <MemoryRouter>
        <Layout chromeHeader={<div data-testid="chrome">Nav</div>}>
          <span>Content</span>
        </Layout>
      </MemoryRouter>,
    )

    const mainInner = container.querySelector('main')?.firstElementChild
    expect(mainInner).toBeTruthy()
    expect(mainInner?.className).toMatch(/pt-20/)
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
    expect(screen.getByText(/Privacy/)).toBeTruthy()
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
