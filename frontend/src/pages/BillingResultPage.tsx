import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { getCheckoutStatus, getPurchases } from '../lib/api/billing'
import { catalogApiUserMessage } from '../lib/apiUserMessages'
import {
  clearCheckoutPendingPurchaseId,
  readCheckoutPendingPurchaseId,
} from '../lib/checkoutPendingPurchase'
import { billingCancelMessage, billingSuccessMessage } from '../lib/purchaseCopy'
import { usePageTitle } from '../lib/page-title'
import type { PurchaseRecord } from '../lib/api/types'
import './BillingReturnPage.css'

const STATUS_POLL_MS = 1500
const PURCHASE_POLL_MS = 2000
const MAX_ATTEMPTS = 40

type ResultPhase = 'loading' | 'success' | 'canceled' | 'pending' | 'error'

function isTargetPurchasePaid(
  purchases: PurchaseRecord[],
  pendingPurchaseId: string | null,
): boolean {
  const isPaid = (row: PurchaseRecord) => (row.status ?? '').trim().toLowerCase() === 'paid'
  if (pendingPurchaseId) {
    return purchases.some((row) => row.id === pendingPurchaseId && isPaid(row))
  }
  return purchases.some(isPaid)
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
    let statusAttempts = 0
    let purchaseAttempts = 0

    const pendingPurchaseId = readCheckoutPendingPurchaseId()

    const finishSuccess = () => {
      if (!cancelled) {
        clearCheckoutPendingPurchaseId()
        setPhase('success')
      }
    }

    const pollPurchases = async () => {
      while (!cancelled && purchaseAttempts < MAX_ATTEMPTS) {
        purchaseAttempts += 1
        try {
          const purchases = await getPurchases()
          if (isTargetPurchasePaid(purchases, pendingPurchaseId)) {
            finishSuccess()
            return
          }
        } catch {
          // keep polling while checkout status may still be settling
        }
        await new Promise((r) => setTimeout(r, PURCHASE_POLL_MS))
      }
      if (!cancelled) {
        setPhase('pending')
        setMessage(billingSuccessMessage)
      }
    }

    const run = async () => {
      while (!cancelled && statusAttempts < MAX_ATTEMPTS) {
        statusAttempts += 1
        try {
          const { status } = await getCheckoutStatus(checkoutId)
          const normalized = (status ?? '').trim().toLowerCase()
          if (normalized === 'pending') {
            await new Promise((r) => setTimeout(r, STATUS_POLL_MS))
            continue
          }
          if (normalized === 'failed' || normalized === 'error') {
            clearCheckoutPendingPurchaseId()
            setPhase('error')
            setMessage('Payment could not be completed. You can try checkout again from the catalog.')
            return
          }
          void pollPurchases()
          return
        } catch (err) {
          if (!cancelled) {
            setPhase('error')
            setMessage(catalogApiUserMessage(err, 'checkout'))
          }
          return
        }
      }
      if (!cancelled) {
        setPhase('pending')
        setMessage(billingSuccessMessage)
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
            Please wait…
          </p>
        ) : null}
        <Link to="/courses" className="btn btn-primary">
          Browse courses
        </Link>
        {phase === 'success' ? (
          <Link to="/dashboard" className="btn btn-ghost" style={{ marginLeft: 12 }}>
            Go to dashboard
          </Link>
        ) : null}
      </div>
    </div>
  )
}
