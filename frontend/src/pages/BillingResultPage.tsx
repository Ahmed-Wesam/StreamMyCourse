import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { getPurchases } from '../lib/api/billing'
import {
  clearCheckoutPendingPurchaseId,
  readCheckoutPendingPurchaseId,
} from '../lib/checkoutPendingPurchase'
import {
  billingCancelMessage,
  billingPaymentIncompleteMessage,
  billingStayOnPageMessage,
  billingSuccessMessage,
} from '../lib/purchaseCopy'
import { usePageTitle } from '../lib/page-title'
import type { PurchaseRecord } from '../lib/api/types'
import './BillingReturnPage.css'

const PURCHASE_POLL_MS = 2000
const PURCHASE_MAX_ATTEMPTS = 90

type ResultPhase = 'loading' | 'success' | 'canceled' | 'pending' | 'error'

function isTargetPurchasePaid(
  purchases: PurchaseRecord[],
  pendingPurchaseId: string | null,
): boolean {
  const isPaid = (row: PurchaseRecord) => (row.status ?? '').trim().toLowerCase() === 'paid'
  if (!pendingPurchaseId) {
    return false
  }
  return purchases.some((row) => row.id === pendingPurchaseId && isPaid(row))
}

export default function BillingResultPage() {
  usePageTitle('Payment')
  const [searchParams] = useSearchParams()
  const checkoutId = (searchParams.get('id') ?? '').trim()
  const canceledHint = searchParams.get('canceled') === '1'

  const [phase, setPhase] = useState<ResultPhase>(() =>
    !checkoutId && canceledHint ? 'canceled' : 'loading',
  )
  const [message, setMessage] = useState<string | null>(null)

  const heading = useMemo(() => {
    if (phase === 'success') return 'Payment received'
    if (phase === 'canceled') return 'Checkout canceled'
    if (phase === 'error') return 'Payment issue'
    if (phase === 'pending') return 'Confirming payment'
    return 'Processing payment'
  }, [phase])

  useEffect(() => {
    if (!checkoutId) {
      if (!canceledHint) {
        setPhase('error')
        setMessage('Missing checkout reference. Return from the payment page or contact support.')
      }
      return
    }

    let cancelled = false
    let purchaseAttempts = 0
    const pendingPurchaseId = readCheckoutPendingPurchaseId()

    const finishSuccess = () => {
      if (!cancelled) {
        clearCheckoutPendingPurchaseId()
        setPhase('success')
      }
    }

    const run = async () => {
      setPhase('pending')
      while (!cancelled && purchaseAttempts < PURCHASE_MAX_ATTEMPTS) {
        purchaseAttempts += 1
        try {
          const purchases = await getPurchases()
          if (isTargetPurchasePaid(purchases, pendingPurchaseId)) {
            finishSuccess()
            return
          }
        } catch {
          // HyperPay webhook may still be in flight
        }
        await new Promise((r) => setTimeout(r, PURCHASE_POLL_MS))
      }
      if (!cancelled) {
        clearCheckoutPendingPurchaseId()
        setPhase('error')
        setMessage(billingPaymentIncompleteMessage)
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [checkoutId, canceledHint])

  const bodyCopy =
    phase === 'success'
      ? billingSuccessMessage
      : phase === 'canceled'
        ? billingCancelMessage
        : message

  return (
    <div className="pg-billing-return" data-testid="billing-result-page">
      <div className="wrap billing-return-inner">
        <h1>{heading}</h1>
        {bodyCopy ? <p>{bodyCopy}</p> : null}
        {phase === 'loading' || phase === 'pending' ? (
          <p className="billing-result-status" role="status">
            {billingStayOnPageMessage}
          </p>
        ) : null}
        {phase === 'success' ? (
          <Link to="/dashboard" className="btn btn-primary">
            Go to dashboard
          </Link>
        ) : null}
      </div>
    </div>
  )
}
