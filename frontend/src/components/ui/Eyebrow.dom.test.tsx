/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Eyebrow } from './Eyebrow'

describe('Eyebrow', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders children', () => {
    render(<Eyebrow>Featured</Eyebrow>)
    expect(screen.getByText('Featured')).toBeTruthy()
  })
})
