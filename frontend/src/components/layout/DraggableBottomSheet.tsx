import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react'
import {
  bottomSheetDismissProbeHeight,
  bottomSheetFullHeight,
  bottomSheetPartialHeight,
  resolveBottomSheetSnapAfterDrag,
} from '../../lib/bottomSheetSnap'

type DraggableBottomSheetProps = {
  open: boolean
  onClose: () => void
  children: ReactNode
  ariaLabel: string
}

function readViewportHeight(): number {
  if (typeof window === 'undefined') return 640
  return window.visualViewport?.height ?? window.innerHeight
}

export function DraggableBottomSheet({ open, onClose, children, ariaLabel }: DraggableBottomSheetProps) {
  const [snap, setSnap] = useState<'partial' | 'full'>('partial')
  const [isDragging, setIsDragging] = useState(false)
  const [dragVisualHeight, setDragVisualHeight] = useState<number | null>(null)
  const [viewportHeight, setViewportHeight] = useState(readViewportHeight)
  const [measuredSheetHeight, setMeasuredSheetHeight] = useState(0)
  const sheetRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)
  const dragStart = useRef({ y: 0, height: 0 })
  const dragHeightRef = useRef<number | null>(null)
  const activePointerId = useRef<number | null>(null)
  const dragFrameRef = useRef<number | null>(null)
  const pendingMeasureIdRef = useRef(0)
  const pendingMeasureRef = useRef<{
    id: number
    pointerId: number
    rafIds: number[]
    pointerStillDown: boolean
    removeEarlyPointerListeners: () => void
  } | null>(null)

  const partialCap = bottomSheetPartialHeight(viewportHeight)
  const fullHeight = bottomSheetFullHeight(viewportHeight)

  const syncMeasuredHeight = useCallback(() => {
    const el = sheetRef.current
    if (!el) return 0
    const next = el.offsetHeight > 0 ? el.offsetHeight : el.getBoundingClientRect().height
    if (next > 0) {
      setMeasuredSheetHeight(next)
      return next
    }
    return 0
  }, [])

  const cancelPendingPointerMeasure = useCallback(() => {
    const pending = pendingMeasureRef.current
    if (!pending) return
    pending.removeEarlyPointerListeners()
    for (const rafId of pending.rafIds) {
      cancelAnimationFrame(rafId)
    }
    pendingMeasureRef.current = null
  }, [])

  useEffect(() => {
    cancelPendingPointerMeasure()
    if (!open) return
    setSnap('partial')
    setIsDragging(false)
    setDragVisualHeight(null)
    setMeasuredSheetHeight(0)
    dragHeightRef.current = null
    dragging.current = false
    activePointerId.current = null
    if (dragFrameRef.current != null) {
      cancelAnimationFrame(dragFrameRef.current)
      dragFrameRef.current = null
    }
  }, [open, cancelPendingPointerMeasure])

  useEffect(() => {
    if (!open) return
    const syncViewport = () => setViewportHeight(readViewportHeight())
    syncViewport()
    window.addEventListener('resize', syncViewport)
    window.visualViewport?.addEventListener('resize', syncViewport)
    return () => {
      window.removeEventListener('resize', syncViewport)
      window.visualViewport?.removeEventListener('resize', syncViewport)
    }
  }, [open])

  useLayoutEffect(() => {
    if (!open) return
    syncMeasuredHeight()
  }, [open, children, snap, syncMeasuredHeight])

  useEffect(() => {
    if (!open) return
    const el = sheetRef.current
    if (!el || typeof ResizeObserver === 'undefined') return

    const observer = new ResizeObserver(() => {
      syncMeasuredHeight()
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [open, children, snap, syncMeasuredHeight])

  const readSheetHeight = useCallback(() => {
    const el = sheetRef.current
    if (el) {
      const live = el.offsetHeight > 0 ? el.offsetHeight : el.getBoundingClientRect().height
      if (live > 0) return live
    }
    if (measuredSheetHeight > 0) return measuredSheetHeight
    return 0
  }, [measuredSheetHeight])

  const measureSheetHeightForInteraction = useCallback(() => {
    const synced = syncMeasuredHeight()
    if (synced > 0) return synced

    const el = sheetRef.current
    if (el) {
      const live = el.offsetHeight > 0 ? el.offsetHeight : el.getBoundingClientRect().height
      if (live > 0) {
        setMeasuredSheetHeight(live)
        return live
      }
      const scroll = el.scrollHeight
      if (scroll > 0) {
        setMeasuredSheetHeight(scroll)
        return scroll
      }
    }

    return readSheetHeight()
  }, [readSheetHeight, syncMeasuredHeight])

  const settledHeight = snap === 'full' ? fullHeight : partialCap
  const displayedHeight =
    dragVisualHeight ?? (snap === 'full' ? fullHeight : measuredSheetHeight)
  const useExplicitHeight = isDragging || snap === 'full'

  const scheduleDragVisualUpdate = useCallback(() => {
    if (dragFrameRef.current != null) return
    dragFrameRef.current = requestAnimationFrame(() => {
      dragFrameRef.current = null
      if (dragHeightRef.current != null) {
        setDragVisualHeight(dragHeightRef.current)
      }
    })
  }, [])

  const endDrag = useCallback(
    (releaseHeight: number) => {
      dragging.current = false
      activePointerId.current = null
      setIsDragging(false)
      setDragVisualHeight(null)
      dragHeightRef.current = null
      if (dragFrameRef.current != null) {
        cancelAnimationFrame(dragFrameRef.current)
        dragFrameRef.current = null
      }
      const resolved = resolveBottomSheetSnapAfterDrag(
        releaseHeight,
        viewportHeight,
        dragStart.current.height,
      )
      if (resolved === 'closed') {
        onClose()
        return
      }
      setSnap(resolved)
    },
    [onClose, viewportHeight],
  )

  const applyDragHeight = useCallback(
    (clientY: number) => {
      const delta = dragStart.current.y - clientY
      const next = Math.max(0, Math.min(fullHeight, dragStart.current.height + delta))
      dragHeightRef.current = next
      scheduleDragVisualUpdate()
    },
    [fullHeight, scheduleDragVisualUpdate],
  )

  useEffect(() => {
    if (!isDragging) return

    const onWindowPointerMove = (e: PointerEvent) => {
      if (!dragging.current || e.pointerId !== activePointerId.current) return
      applyDragHeight(e.clientY)
    }

    const onWindowPointerEnd = (e: PointerEvent) => {
      if (!dragging.current || e.pointerId !== activePointerId.current) return
      endDrag(dragHeightRef.current ?? dragStart.current.height)
    }

    window.addEventListener('pointermove', onWindowPointerMove)
    window.addEventListener('pointerup', onWindowPointerEnd)
    window.addEventListener('pointercancel', onWindowPointerEnd)
    return () => {
      window.removeEventListener('pointermove', onWindowPointerMove)
      window.removeEventListener('pointerup', onWindowPointerEnd)
      window.removeEventListener('pointercancel', onWindowPointerEnd)
    }
  }, [isDragging, applyDragHeight, endDrag])

  const beginPointerDrag = useCallback(
    (handle: HTMLDivElement, pointerId: number, clientY: number, startHeight: number) => {
      handle.setPointerCapture?.(pointerId)
      activePointerId.current = pointerId
      dragging.current = true
      dragStart.current = { y: clientY, height: startHeight }
      dragHeightRef.current = startHeight
      setIsDragging(true)
      setDragVisualHeight(startHeight)
    },
    [],
  )

  const tryBeginPointerDrag = useCallback(
    (
      handle: HTMLDivElement,
      pointerId: number,
      clientY: number,
      onMeasured: () => void,
    ): boolean => {
      const startHeight = measureSheetHeightForInteraction()
      if (startHeight <= 0) return false
      onMeasured()
      beginPointerDrag(handle, pointerId, clientY, startHeight)
      return true
    },
    [beginPointerDrag, measureSheetHeightForInteraction],
  )

  const scheduleDeferredPointerMeasure = useCallback(
    (
      handle: HTMLDivElement,
      pointerId: number,
      clientY: number,
      preventDefault: () => void,
    ) => {
      cancelPendingPointerMeasure()

      const measureId = ++pendingMeasureIdRef.current

      const clearEarlyPointerListeners = () => {
        window.removeEventListener('pointerup', onEarlyPointerEnd)
        window.removeEventListener('pointercancel', onEarlyPointerEnd)
      }

      const onEarlyPointerEnd = (event: PointerEvent) => {
        if (event.pointerId !== pointerId) return
        const active = pendingMeasureRef.current
        if (active?.id === measureId) {
          active.pointerStillDown = false
        }
        cancelPendingPointerMeasure()
      }

      const pending = {
        id: measureId,
        pointerId,
        rafIds: [] as number[],
        pointerStillDown: true,
        removeEarlyPointerListeners: clearEarlyPointerListeners,
      }
      pendingMeasureRef.current = pending

      const isPending = () => pendingMeasureRef.current?.id === measureId

      window.addEventListener('pointerup', onEarlyPointerEnd)
      window.addEventListener('pointercancel', onEarlyPointerEnd)

      const tryMeasure = (): boolean => {
        if (!isPending()) return true
        if (dragging.current) {
          cancelPendingPointerMeasure()
          return true
        }
        if (tryBeginPointerDrag(handle, pointerId, clientY, preventDefault)) {
          cancelPendingPointerMeasure()
          return true
        }
        return false
      }

      const finishUnmeasured = () => {
        if (!isPending()) return
        const pointerStillDown = pending.pointerStillDown
        cancelPendingPointerMeasure()
        if (tryBeginPointerDrag(handle, pointerId, clientY, preventDefault)) return
        if (pointerStillDown) return
        preventDefault()
        onClose()
      }

      const raf1 = requestAnimationFrame(() => {
        if (tryMeasure()) return
        const raf2 = requestAnimationFrame(() => {
          if (!isPending()) return
          if (dragging.current) {
            cancelPendingPointerMeasure()
            return
          }
          finishUnmeasured()
        })
        if (isPending()) pending.rafIds.push(raf2)
      })
      pending.rafIds.push(raf1)
    },
    [cancelPendingPointerMeasure, onClose, tryBeginPointerDrag],
  )

  const onHandlePointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (dragging.current || isDragging) return

    const handle = e.currentTarget
    const { pointerId, clientY } = e
    const preventDefault = () => e.preventDefault()

    if (tryBeginPointerDrag(handle, pointerId, clientY, preventDefault)) return

    scheduleDeferredPointerMeasure(handle, pointerId, clientY, preventDefault)
  }

  const onHandleKeyDown = (e: ReactKeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
      return
    }

    if (e.key === 'ArrowUp' || e.key === 'Home') {
      e.preventDefault()
      setSnap('full')
      return
    }

    if (e.key === 'ArrowDown' || e.key === 'End') {
      e.preventDefault()
      if (snap === 'full') {
        setSnap('partial')
        return
      }

      const currentHeight = measureSheetHeightForInteraction()
      if (currentHeight <= 0) {
        onClose()
        return
      }

      const resolved = resolveBottomSheetSnapAfterDrag(
        bottomSheetDismissProbeHeight(currentHeight, viewportHeight),
        viewportHeight,
        currentHeight,
      )
      if (resolved === 'closed') onClose()
    }
  }

  if (!open) return null

  const roundedHeight = Math.round(displayedHeight)
  const snapValueText =
    snap === 'full'
      ? `Full screen, ${fullHeight} pixels tall`
      : `Partial height, ${roundedHeight} pixels tall (max ${partialCap})`

  const sheetStyle: CSSProperties = useExplicitHeight
    ? { height: `${isDragging ? (dragVisualHeight ?? settledHeight) : settledHeight}px` }
    : { maxHeight: `${partialCap}px` }

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
    >
      <button
        type="button"
        className="absolute inset-0 z-0 bg-slate-900/50 backdrop-blur-[2px]"
        aria-label="Close sheet"
        onClick={onClose}
      />
      <div
        ref={sheetRef}
        data-testid="sheet-panel"
        className={`relative z-10 flex flex-col overflow-hidden rounded-t-2xl bg-white shadow-2xl ${
          useExplicitHeight && !isDragging ? 'transition-[height] duration-300 ease-out' : ''
        }`}
        style={sheetStyle}
      >
        <div
          role="slider"
          tabIndex={0}
          aria-orientation="vertical"
          aria-valuemin={0}
          aria-valuemax={fullHeight}
          aria-valuenow={roundedHeight}
          aria-valuetext={snapValueText}
          aria-label="Drag to resize or dismiss. Arrow up expands, arrow down collapses or closes."
          className="flex shrink-0 touch-none cursor-grab active:cursor-grabbing justify-center px-4 pt-2 pb-1 outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          onPointerDown={onHandlePointerDown}
          onKeyDown={onHandleKeyDown}
        >
          <div className="flex min-h-11 w-full items-center justify-center">
            <div className="h-1.5 w-10 rounded-full bg-slate-300" aria-hidden="true" />
          </div>
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  )
}
