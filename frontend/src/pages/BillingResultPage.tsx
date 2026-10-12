import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getCheckoutStatus } from '../lib/api/billing'
import {
  clearCheckoutPendingPurchaseId,
  readCheckoutPendingContext,
  type CheckoutPendingContext,
} from '../lib/checkoutPendingPurchase'
import {
  billingConfirmingMessage,
  billingEnrolledMessage,
  billingPaymentFailedMessage,
} from '../lib/purchaseCopy'
import { usePageTitle } from '../lib/page-title'
import './BillingReturnPage.css'

const STATUS_POLL_MS = 1500
const MAX_ATTEMPTS = 80

type ResultPhase = 'confirming' | 'enrolled' | 'failed'

export default function BillingResultPage() {
  usePageTitle('Payment')
  const [phase, setPhase] = useState<ResultPhase>('confirming')
  const [pendingCtx, setPendingCtx] = useState<CheckoutPendingContext | null>(() =>
    readCheckoutPendingContext(),
  )

  const enrollHref =
    pendingCtx?.productType === 'course' && pendingCtx.courseId?.trim()
      ? `/courses/${pendingCtx.courseId.trim()}`
      : '/dashboard'

  const enrollCtaLabel =
    pendingCtx?.productType === 'course' && pendingCtx.courseId?.trim()
      ? 'Continue to your course'
      : 'Go to dashboard'

  useEffect(() => {
    const ctx = readCheckoutPendingContext()
    setPendingCtx(ctx)
    const purchaseId = ctx?.purchaseId?.trim() ?? ''
    if (!purchaseId) {
      return
    }

    let cancelled = false
    let attempts = 0

    const run = async () => {
      while (!cancelled && attempts < MAX_ATTEMPTS) {
        attempts += 1
        try {
          const { status } = await getCheckoutStatus(purchaseId)
          const normalized = (status ?? '').trim().toLowerCase()
          if (normalized === 'pending') {
            await new Promise((r) => setTimeout(r, STATUS_POLL_MS))
            continue
          }
          if (normalized === 'paid') {
            clearCheckoutPendingPurchaseId()
            setPhase('enrolled')
            return
          }
          if (normalized === 'failed') {
            clearCheckoutPendingPurchaseId()
            setPhase('failed')
            return
          }
          await new Promise((r) => setTimeout(r, STATUS_POLL_MS))
        } catch {
          await new Promise((r) => setTimeout(r, STATUS_POLL_MS))
        }
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [])

  const heading =
    phase === 'enrolled'
      ? billingEnrolledMessage
      : phase === 'failed'
        ? billingPaymentFailedMessage
        : billingConfirmingMessage

  return (
    <div className="pg-billing-return" data-testid="billing-result-page">
      <div className="wrap billing-return-inner">
        <h1>{heading}</h1>
        {phase === 'confirming' ? (
          <p className="billing-result-status" role="status">
            Please wait…
          </p>
        ) : null}
        {phase === 'enrolled' ? (
          <Link to={enrollHref} className="btn btn-primary">
            {enrollCtaLabel}
          </Link>
        ) : null}
        {phase === 'failed' ? (
          <Link to="/courses" className="btn btn-primary">
            Try again
          </Link>
        ) : null}
        {phase !== 'enrolled' ? (
          <Link to="/courses" className="btn btn-ghost" style={{ marginLeft: 12 }}>
            Browse courses
          </Link>
        ) : null}
      </div>
    </div>
  )
}
