import { useCallback, useEffect, useState } from 'react'

import { getPurchases } from '../../lib/api/billing'
import type { PurchaseRecord } from '../../lib/api/types'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { formatUsdMinor } from '../../lib/formatUsdMinor'
import { usePageTitle } from '../../lib/page-title'
import { shouldSuppressInlineSessionSupersededMessage } from '../../lib/session-superseded-inline'

type PageState =
  | { status: 'loading' }
  | { status: 'superseded' }
  | { status: 'error'; message: string }
  | { status: 'ready'; purchases: PurchaseRecord[] }

function formatProductLabel(row: PurchaseRecord): string {
  if (row.productType === 'bundle') return 'Research Mastery Bundle'
  if (row.productType === 'course') return 'Single course'
  return row.productType
}

function formatStatusLabel(status: string): string {
  const normalized = status.trim().toLowerCase()
  if (normalized === 'paid') return 'Paid'
  if (normalized === 'pending') return 'Pending'
  if (normalized === 'failed') return 'Failed'
  return status
}

function formatPurchasedAt(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function AccountPurchasesPage() {
  usePageTitle('My purchases')
  const [state, setState] = useState<PageState>({ status: 'loading' })

  const load = useCallback(async () => {
    setState({ status: 'loading' })
    try {
      const purchases = await getPurchases()
      setState({ status: 'ready', purchases })
    } catch (err) {
      if (shouldSuppressInlineSessionSupersededMessage(err)) {
        setState({ status: 'superseded' })
        return
      }
      setState({ status: 'error', message: catalogApiUserMessage(err, 'loadPurchases') })
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <section className="text-rs-ink" data-testid="account-purchases">
      <h2 className="text-xl font-extrabold tracking-tight">My purchases</h2>
      <p className="mt-2 text-sm text-rs-body">One-time course and bundle purchases linked to your account.</p>

      {state.status === 'loading' ? <p className="mt-6 text-sm text-rs-body">Loading purchases…</p> : null}

      {state.status === 'superseded' ? (
        <p className="mt-6 text-sm text-rs-body">Your session was replaced by a newer sign-in. Refresh after signing in again.</p>
      ) : null}

      {state.status === 'error' ? (
        <div className="mt-6">
          <p className="text-sm text-red-700" role="alert">
            {state.message}
          </p>
        </div>
      ) : null}

      {state.status === 'ready' && state.purchases.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-rs-line bg-white p-6" data-testid="purchases-empty">
          <p className="text-sm text-rs-body">You have not purchased any courses yet.</p>
          <a
            href="/courses"
            className="mt-4 inline-flex text-sm font-bold text-rs-blue no-underline hover:opacity-90"
          >
            Browse courses
          </a>
        </div>
      ) : null}

      {state.status === 'ready' && state.purchases.length > 0 ? (
        <ul className="mt-6 divide-y divide-rs-line rounded-2xl border border-rs-line bg-white">
          {state.purchases.map((row) => (
            <li key={row.id} className="px-5 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-bold text-rs-ink">{formatProductLabel(row)}</p>
                <p className="text-sm font-semibold text-rs-blue">{formatUsdMinor(row.amountMinor)}</p>
              </div>
              <p className="mt-1 text-xs text-rs-muted">
                {formatStatusLabel(row.status)} · {formatPurchasedAt(row.createdAt)}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
