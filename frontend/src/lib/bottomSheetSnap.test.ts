import { describe, expect, it } from 'vitest'
import {
  bottomSheetDismissProbeHeight,
  bottomSheetFullHeight,
  bottomSheetPartialHeight,
  resolveBottomSheetSnapAfterDrag,
} from './bottomSheetSnap'

describe('bottomSheetSnap', () => {
  const viewport = 800
  const partial = 704

  it('computes partial height capped at 720px', () => {
    expect(bottomSheetPartialHeight(800)).toBe(704)
    expect(bottomSheetPartialHeight(1000)).toBe(720)
  })

  it('uses full viewport for expanded height', () => {
    expect(bottomSheetFullHeight(800)).toBe(800)
  })

  it('dismisses when dragged near the absolute bottom', () => {
    expect(resolveBottomSheetSnapAfterDrag(100, viewport, partial)).toBe('closed')
  })

  it('dismisses from partial cap after a moderate downward drag', () => {
    expect(resolveBottomSheetSnapAfterDrag(500, viewport, partial)).toBe('closed')
  })

  it('stays partial when only slightly dragged down from partial cap', () => {
    expect(resolveBottomSheetSnapAfterDrag(650, viewport, partial)).toBe('partial')
  })

  it('snaps to full when dragged above expand midpoint from partial cap', () => {
    expect(resolveBottomSheetSnapAfterDrag(760, viewport, partial)).toBe('full')
  })

  it('snaps to full when dragged up from a short content-sized sheet', () => {
    expect(resolveBottomSheetSnapAfterDrag(600, viewport, 200)).toBe('full')
  })

  it('stays partial when a short sheet is only dragged up slightly', () => {
    expect(resolveBottomSheetSnapAfterDrag(350, viewport, 200)).toBe('partial')
  })

  it('snaps to partial when dragged down from full without enough travel to dismiss', () => {
    expect(resolveBottomSheetSnapAfterDrag(650, viewport, viewport)).toBe('partial')
  })

  it('keyboard dismiss probe resolves to closed', () => {
    const probe = bottomSheetDismissProbeHeight(partial, viewport)
    expect(resolveBottomSheetSnapAfterDrag(probe, viewport, partial)).toBe('closed')
  })
})
