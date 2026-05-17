/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { bottomSheetPartialHeight } from '../../lib/bottomSheetSnap'
import { DraggableBottomSheet } from './DraggableBottomSheet'

describe('DraggableBottomSheet', () => {
  afterEach(() => cleanup())

  it('applies the JS partial cap as maxHeight in partial mode', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    render(
      <DraggableBottomSheet open onClose={vi.fn()} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )
    const sheet = screen.getByTestId('sheet-panel')
    expect(sheet.style.maxHeight).toBe(`${bottomSheetPartialHeight(800)}px`)
    expect(sheet.style.height).toBe('')
  })

  it('renders a drag handle when open', () => {
    render(
      <DraggableBottomSheet open onClose={vi.fn()} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )
    expect(screen.getByRole('dialog', { name: 'Test sheet' })).toBeTruthy()
    expect(screen.getByRole('slider', { name: /Drag to resize or dismiss/i })).toBeTruthy()
    expect(screen.getByText('Sheet body')).toBeTruthy()
  })

  it('calls onClose when backdrop is clicked', () => {
    const onClose = vi.fn()
    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Close sheet' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('ignores a second pointerdown while a drag is already active', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    const partial = bottomSheetPartialHeight(800)

    render(
      <DraggableBottomSheet open onClose={vi.fn()} ariaLabel="Test sheet">
        <div style={{ height: partial }} data-testid="tall-body" />
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: partial })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 400, pointerId: 1 })
    fireEvent.pointerMove(window, { clientY: 300, pointerId: 1 })

    fireEvent.pointerDown(handle, { clientY: 200, pointerId: 2 })
    fireEvent.pointerUp(window, { clientY: 300, pointerId: 1 })

    expect(sheet.style.height).toBe('800px')
  })

  it('ignores pointerup from a different pointer id during drag', () => {
    const onClose = vi.fn()
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    const partial = bottomSheetPartialHeight(800)

    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <div style={{ height: partial }} data-testid="tall-body" />
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: partial })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 100, pointerId: 1 })
    fireEvent.pointerMove(window, { clientY: 320, pointerId: 1 })
    fireEvent.pointerUp(window, { clientY: 320, pointerId: 2 })
    expect(onClose).not.toHaveBeenCalled()

    fireEvent.pointerUp(window, { clientY: 320, pointerId: 1 })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('dismisses after a moderate downward drag from partial height', () => {
    const onClose = vi.fn()
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    const partial = bottomSheetPartialHeight(800)

    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <div style={{ height: partial }} data-testid="tall-body" />
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: partial })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 100, pointerId: 1 })
    fireEvent.pointerMove(window, { clientY: 320, pointerId: 1 })
    fireEvent.pointerUp(window, { clientY: 320, pointerId: 1 })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('snaps to full after an upward drag', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    const partial = bottomSheetPartialHeight(800)

    render(
      <DraggableBottomSheet open onClose={vi.fn()} ariaLabel="Test sheet">
        <div style={{ height: partial }} data-testid="tall-body" />
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: partial })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 400, pointerId: 1 })
    fireEvent.pointerMove(window, { clientY: 50, pointerId: 1 })
    fireEvent.pointerUp(window, { clientY: 50, pointerId: 1 })

    expect(sheet.style.height).toBe('800px')
  })

  it('closes on ArrowDown from partial when the sheet height cannot be measured', () => {
    const onClose = vi.fn()
    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: 0 })
    Object.defineProperty(sheet, 'scrollHeight', { configurable: true, value: 0 })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.keyDown(handle, { key: 'ArrowDown' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not close or start drag when the pointer is released before deferred measure', async () => {
    const onClose = vi.fn()
    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: 0 })
    Object.defineProperty(sheet, 'scrollHeight', { configurable: true, value: 0 })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 100, pointerId: 1 })
    fireEvent.pointerUp(window, { clientY: 100, pointerId: 1 })

    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
    })

    expect(onClose).not.toHaveBeenCalled()
    expect(sheet.style.height).toBe('')
  })

  it('does not close on pointerdown while the finger is still down and height stays unmeasured', async () => {
    const onClose = vi.fn()
    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: 0 })
    Object.defineProperty(sheet, 'scrollHeight', { configurable: true, value: 0 })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 100, pointerId: 1 })

    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
    })

    expect(onClose).not.toHaveBeenCalled()
  })

  it('removes early pointer listeners when the sheet closes during deferred measure', async () => {
    const onClose = vi.fn()
    const { rerender } = render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: 0 })
    Object.defineProperty(sheet, 'scrollHeight', { configurable: true, value: 0 })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 100, pointerId: 1 })

    rerender(
      <DraggableBottomSheet open={false} onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )

    rerender(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )

    const reopenedSheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(reopenedSheet, 'offsetHeight', { configurable: true, value: 0 })
    Object.defineProperty(reopenedSheet, 'scrollHeight', { configurable: true, value: 0 })

    const reopenedHandle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(reopenedHandle, { clientY: 100, pointerId: 1 })

    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
    })

    fireEvent.pointerUp(window, { clientY: 100, pointerId: 1 })

    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
    })

    expect(onClose).not.toHaveBeenCalled()
  })

  it('dismisses on ArrowDown from partial using the same snap rules as drag', () => {
    const onClose = vi.fn()
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    const partial = bottomSheetPartialHeight(800)

    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <div style={{ height: partial }} data-testid="tall-body" />
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: partial })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.keyDown(handle, { key: 'ArrowDown' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('closes on Escape from the drag handle', () => {
    const onClose = vi.fn()
    render(
      <DraggableBottomSheet open onClose={onClose} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )
    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.keyDown(handle, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('snaps to full after an upward drag from a short content-sized sheet', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    const shortContent = 200

    render(
      <DraggableBottomSheet open onClose={vi.fn()} ariaLabel="Test sheet">
        <div style={{ height: shortContent }} data-testid="short-body" />
      </DraggableBottomSheet>,
    )

    const sheet = screen.getByTestId('sheet-panel')
    Object.defineProperty(sheet, 'offsetHeight', { configurable: true, value: shortContent })

    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.pointerDown(handle, { clientY: 500, pointerId: 1 })
    fireEvent.pointerMove(window, { clientY: 100, pointerId: 1 })
    fireEvent.pointerUp(window, { clientY: 100, pointerId: 1 })

    expect(sheet.style.height).toBe('800px')
  })

  it('expands to full on ArrowUp from the drag handle', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    render(
      <DraggableBottomSheet open onClose={vi.fn()} ariaLabel="Test sheet">
        <p>Sheet body</p>
      </DraggableBottomSheet>,
    )
    const handle = screen.getByRole('slider', { name: /Drag to resize or dismiss/i })
    fireEvent.keyDown(handle, { key: 'ArrowUp' })
    const sheet = screen.getByTestId('sheet-panel')
    expect(sheet.style.height).toBe('800px')
  })
})
