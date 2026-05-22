import type { ReactNode } from 'react'
import { Suspense } from 'react'

export function RouteChunkFallback() {
  return (
    <div
      className="mx-auto flex w-full max-w-md flex-col items-center justify-center px-4 py-12"
      role="status"
      aria-live="polite"
    >
      <div className="w-full rounded-2xl border border-slate-200/80 bg-white/90 p-8 shadow-sm shadow-slate-200/60 backdrop-blur-sm">
        <p className="text-center text-sm font-medium text-slate-600">Loading…</p>
        <div className="mx-auto mt-4 h-1.5 w-40 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-emerald-500/80" />
        </div>
      </div>
    </div>
  )
}

export function LazyRoute({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteChunkFallback />}>{children}</Suspense>
}
