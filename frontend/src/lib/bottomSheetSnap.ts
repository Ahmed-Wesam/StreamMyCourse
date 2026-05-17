/** Default open height cap — matches prior `max-h-[min(88dvh,720px)]`. */
const BOTTOM_SHEET_PARTIAL_RATIO = 0.88
const BOTTOM_SHEET_PARTIAL_MAX_PX = 720
/** Absolute floor: release at or below this fraction of viewport dismisses. */
const BOTTOM_SHEET_DISMISS_RATIO = 0.18
/** Fraction of (dragStart − dismiss floor) that must be dragged down to dismiss. */
const BOTTOM_SHEET_DISMISS_DRAG_FRACTION = 0.35
/** Fraction of travel from dragStart toward full required to snap expanded. */
const BOTTOM_SHEET_EXPAND_DRAG_FRACTION = 0.5

type BottomSheetSnap = 'closed' | 'partial' | 'full'

export function bottomSheetPartialHeight(viewportHeight: number): number {
  return Math.min(viewportHeight * BOTTOM_SHEET_PARTIAL_RATIO, BOTTOM_SHEET_PARTIAL_MAX_PX)
}

export function bottomSheetFullHeight(viewportHeight: number): number {
  return viewportHeight
}

function bottomSheetDismissFromStart(dragStartHeight: number, viewportHeight: number): number {
  const dismissThreshold = viewportHeight * BOTTOM_SHEET_DISMISS_RATIO
  return dragStartHeight - (dragStartHeight - dismissThreshold) * BOTTOM_SHEET_DISMISS_DRAG_FRACTION
}

/** Release height that resolves to `closed` for the same rules as pointer drag. */
export function bottomSheetDismissProbeHeight(dragStartHeight: number, viewportHeight: number): number {
  return Math.max(0, bottomSheetDismissFromStart(dragStartHeight, viewportHeight) - 1)
}

export function resolveBottomSheetSnapAfterDrag(
  releaseHeight: number,
  viewportHeight: number,
  dragStartHeight: number,
): BottomSheetSnap {
  const full = bottomSheetFullHeight(viewportHeight)
  const dismissThreshold = viewportHeight * BOTTOM_SHEET_DISMISS_RATIO

  if (releaseHeight <= dismissThreshold) return 'closed'

  if (releaseHeight <= bottomSheetDismissFromStart(dragStartHeight, viewportHeight)) return 'closed'

  const expandMidpoint =
    dragStartHeight + (full - dragStartHeight) * BOTTOM_SHEET_EXPAND_DRAG_FRACTION
  if (releaseHeight >= expandMidpoint) return 'full'
  return 'partial'
}
