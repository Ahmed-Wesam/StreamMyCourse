/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SessionSupersededBanner } from './SessionSupersededBanner'

describe('SessionSupersededBanner', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders message and calls onDismiss when the side control is clicked', () => {
    const onDismiss = vi.fn()
    render(
      <SessionSupersededBanner message="Signed in elsewhere" onDismiss={onDismiss} />,
    )

    expect(screen.getByTestId('session-superseded-banner')).toBeTruthy()
    expect(screen.getByText('Signed in elsewhere')).toBeTruthy()

    fireEvent.click(screen.getByTestId('session-superseded-banner-dismiss'))
    expect(onDismiss).toHaveBeenCalledTimes(1)
  })
})
