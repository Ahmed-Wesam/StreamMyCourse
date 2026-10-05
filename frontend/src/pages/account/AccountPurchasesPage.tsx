import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getPurchases } from '../../lib/api/billing'
import type { PurchaseRecord } from '../../lib/api/types'
import { catalogApiUserMessage } from '../../lib/apiUserMessages'
import { formatUsdMinor } from '../../lib/formatUsdMinor'
import { usePageTitle } from '../../lib/page-title'
import { shouldSuppressInlineSessionSupersededMessage } from '../../lib/session-superseded-inline'
import { IconArrow, IconBook } from './accountIcons'
import './AccountPage.css'

type PageState =
  | { status: 'loading' }
  | { status: 'superseded' }
  | { status: 'error'; message: string }
  | { status: 'ready'; purchases: PurchaseRecord[] }

function formatProductLabel(row: PurchaseRecord): string {
  if (row.productType === 'bundle') return 'Research Mastery Bundle'
  if (row.productType === 'course') return 'Single course purchase'
  return row.productType
}

function formatStatusClass(status: string): string {
  const normalized = status.trim().toLowerCase()
  if (normalized === 'paid') return 'paid'
  if (normalized === 'pending') return 'pending'
  if (normalized === 'failed') return 'failed'
  return 'pending'
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
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatOrderId(id: string): string {
  const compact = id.replace(/[^a-zA-Z0-9]/g, '').slice(-8).toUpperCase()
  return compact ? `RS-ORD-${compact}` : id
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
    <div data-testid="account-purchases">
      <div className="section-sep">
        <div className="wrap">
          <div className="section-group-header">
            <span className="sg-label">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <rect x="1" y="4" width="22" height="16" rx="2" />
                <line x1="1" y1="10" x2="23" y2="10" />
              </svg>
              Purchases
            </span>
          </div>
        </div>
      </div>

      <section className="db" style={{ paddingTop: 0, paddingBottom: 80 }}>
        <div className="wrap">
          <div className="db-head">
            <div className="ht">
              <h2>Billing &amp; Purchase History</h2>
              <span className="htmeta">Your course purchases</span>
            </div>
          </div>

          {state.status === 'loading' ? (
            <p className="field-hint" role="status">
              Loading purchases…
            </p>
          ) : null}

          {state.status === 'superseded' ? (
            <p className="field-hint" role="status">
              Your session was replaced by a newer sign-in. Refresh after signing in again.
            </p>
          ) : null}

          {state.status === 'error' ? (
            <p className="save-error" role="alert">
              {state.message}
            </p>
          ) : null}

          {state.status === 'ready' ? (
            <div className="acct-card reveal">
              <div className="bill-table-wrap">
                <table className="bill-table">
                  <thead>
                    <tr>
                      <th>Order</th>
                      <th>Date</th>
                      <th>Product</th>
                      <th>Amount</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {state.purchases.length === 0 ? (
                      <tr data-testid="purchases-empty">
                        <td colSpan={5} className="purchases-empty-cell">
                          You have not purchased any courses yet.
                        </td>
                      </tr>
                    ) : (
                      state.purchases.map((row) => (
                        <tr key={row.id}>
                          <td className="order-num">{formatOrderId(row.id)}</td>
                          <td>{formatPurchasedAt(row.createdAt)}</td>
                          <td className="prod-name">{formatProductLabel(row)}</td>
                          <td className="amount-col">{formatUsdMinor(row.amountMinor)}</td>
                          <td>
                            <span className={`bill-status ${formatStatusClass(row.status)}`}>
                              {formatStatusLabel(row.status)}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="bill-upsell">
                <div className="bu-ic">
                  <IconBook />
                </div>
                <div className="bu-info">
                  <b>Unlock More Courses — from $50</b>
                  <span>
                    Individual courses at $50 each, or save with the Research Mastery Bundle at $150 (all four courses).
                  </span>
                </div>
                <Link to="/courses#courses-catalog" className="btn btn-ghost btn-sm" style={{ flex: 'none' }}>
                  Explore Courses
                  <IconArrow />
                </Link>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}
