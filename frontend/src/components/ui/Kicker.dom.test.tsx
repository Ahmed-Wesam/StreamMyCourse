/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Kicker } from './Kicker'

describe('Kicker', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders children', () => {
    render(<Kicker>Our courses</Kicker>)
    expect(screen.getByText('Our courses')).toBeTruthy()
  })
})
