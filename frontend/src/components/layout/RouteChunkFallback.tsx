import type { ReactNode } from 'react'
import { Suspense } from 'react'

import { Card } from '../ui/Card'

export function RouteChunkFallback() {
  return (
    <div
      className="mx-auto flex w-full max-w-md flex-col items-center justify-center px-4 py-12"
      role="status"
      aria-live="polite"
    >
      <Card className="w-full p-8 text-center">
        <p className="text-sm font-semibold text-rs-body">Loading…</p>
        <div className="mx-auto mt-4 h-1.5 w-40 overflow-hidden rounded-full bg-rs-sky-2">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-rs-blue/80" />
        </div>
      </Card>
    </div>
  )
}

export function LazyRoute({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteChunkFallback />}>{children}</Suspense>
}
