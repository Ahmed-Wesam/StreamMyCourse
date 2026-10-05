/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProfileMenu } from './ProfileMenu'

function renderMenu(
  props: Partial<Parameters<typeof ProfileMenu>[0]> = {},
) {
  const onSelect = vi.fn()
  const result = render(
    <MemoryRouter>
      <ProfileMenu
        name="Ada Lovelace"
        subtitle="Student"
        items={[
          { href: '/account', label: 'Account' },
          { label: 'Sign out', onSelect },
        ]}
        {...props}
      />
    </MemoryRouter>,
  )
  return { ...result, onSelect }
}

describe('ProfileMenu', () => {
  afterEach(() => {
    cleanup()
  })

  it('click opens the menu', () => {
    renderMenu()
    const trigger = screen.getByRole('button')
    expect(screen.queryByRole('menu')).toBeNull()

    fireEvent.click(trigger)

    expect(screen.getByRole('menu')).toBeTruthy()
  })

  it('browser Enter and Space activation leaves the menu open', () => {
    renderMenu()
    const trigger = screen.getByRole('button')

    // Buttons fire click after Enter/Space. keydown must not toggle the menu shut.
    fireEvent.keyDown(trigger, { key: 'Enter' })
    fireEvent.click(trigger)
    expect(screen.getByRole('menu')).toBeTruthy()

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()

    fireEvent.keyDown(trigger, { key: ' ' })
    fireEvent.click(trigger)
    expect(screen.getByRole('menu')).toBeTruthy()
  })

  it('outside click closes the menu', () => {
    renderMenu()
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('menu')).toBeTruthy()

    fireEvent.mouseDown(document.body)

    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('Escape closes and returns focus to the trigger', () => {
    renderMenu()
    const trigger = screen.getByRole('button')
    fireEvent.click(trigger)
    expect(screen.getByRole('menu')).toBeTruthy()

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('menu')).toBeNull()
    expect(document.activeElement).toBe(trigger)
  })

  it('items have role="menuitem"', () => {
    renderMenu()
    fireEvent.click(screen.getByRole('button'))

    const menu = screen.getByRole('menu')
    const items = within(menu).getAllByRole('menuitem')
    expect(items.map((el) => el.textContent)).toEqual(['Account', 'Sign out'])
  })

  it('empty name shows "?" initials', () => {
    renderMenu({ name: '' })
    expect(screen.getByRole('button').textContent).toMatch(/\?/)
  })

  it('prototype chrome uses nav-profile, nav-drop, and nav-chev', () => {
    const { container } = renderMenu({ chrome: 'prototype' })
    const trigger = container.querySelector('.nav-profile')
    expect(trigger).toBeTruthy()
    expect(container.querySelector('.nav-bell')).toBeNull()
    expect(trigger?.className ?? '').not.toMatch(/\brelative\b/)

    fireEvent.click(screen.getByRole('button'))

    expect(container.querySelector('.nav-profile.is-open')).toBeTruthy()
    expect(container.querySelector('.nav-drop')).toBeTruthy()
    expect(container.querySelector('.nav-avatar')).toBeTruthy()
    expect(container.querySelector('svg.nav-chev')).toBeTruthy()
    expect(container.querySelector('.nav-drop-h')).toBeTruthy()
  })
})
