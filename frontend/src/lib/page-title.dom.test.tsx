/**
 * @vitest-environment jsdom
 */
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { usePageTitle } from './page-title'

function TitleProbe({ title }: { title?: string }) {
  usePageTitle(title)
  return null
}

describe('usePageTitle', () => {
  afterEach(() => {
    cleanup()
    document.title = ''
  })

  it('sets document.title to "Courses — Research Spectrum"', () => {
    render(<TitleProbe title="Courses" />)
    expect(document.title).toBe('Courses — Research Spectrum')
  })

  it('sets document.title to "Research Spectrum" when title is omitted', () => {
    render(<TitleProbe />)
    expect(document.title).toBe('Research Spectrum')
  })
})
