/**
 * @vitest-environment jsdom
 */
import { cleanup, render, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ScrollToTop } from './ScrollToTop'

function Harness() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<div>Home</div>} />
        <Route path="/next" element={<div>Next</div>} />
      </Routes>
    </>
  )
}

describe('ScrollToTop', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('scrolls window to top on route changes without hash', async () => {
    const scrollTo = vi.fn()
    // jsdom doesn't implement scrollTo; we mock it so we can assert behavior.
    vi.stubGlobal('scrollTo', scrollTo)
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0)
      return 0
    })

    const { rerender } = render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )

    rerender(
      <MemoryRouter initialEntries={['/next']}>
        <Harness />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: 'auto' })
    })
  })

  it('scrolls to an element when navigating to a hash', async () => {
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)

    const el = document.createElement('div')
    el.id = 'target'
    const scrollIntoView = vi.fn()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(el as any).scrollIntoView = scrollIntoView
    document.body.appendChild(el)

    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0)
      return 0
    })

    render(
      <MemoryRouter initialEntries={['/#target']}>
        <Harness />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start' })
    })
    expect(scrollTo).not.toHaveBeenCalled()
  })
})

