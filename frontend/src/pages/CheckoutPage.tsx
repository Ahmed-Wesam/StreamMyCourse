import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { Button } from '../components/ui/Button'
import { createCheckoutSession, getBundle } from '../lib/api/billing'
import { getCourse } from '../lib/api/catalog'
import { hasSignedInIdToken } from '../lib/api/session'
import type { CheckoutProductType } from '../lib/api/types'
import { catalogApiUserMessage } from '../lib/apiUserMessages'
import { formatUsdMinor } from '../lib/formatUsdMinor'
import { isHttpsUrl } from '../lib/isHttpsUrl'
import { usePageTitle } from '../lib/page-title'
import { checkoutLoadingLabel } from '../lib/purchaseCopy'
import { persistReturnPathBeforeHostedUi } from '../lib/post-login-return'

type CheckoutParams =
  | { productType: 'bundle' }
  | { productType: 'course'; courseId: string }

function parseCheckoutParams(searchParams: URLSearchParams): CheckoutParams | null {
  const productType = (searchParams.get('productType') ?? '').trim().toLowerCase()
  if (productType === 'bundle') {
    return { productType: 'bundle' }
  }
  if (productType === 'course') {
    const courseId = (searchParams.get('courseId') ?? '').trim()
    if (!courseId) return null
    return { productType: 'course', courseId }
  }
  return null
}

export default function CheckoutPage() {
  usePageTitle('Checkout')
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const checkoutParams = useMemo(() => parseCheckoutParams(searchParams), [searchParams])

  const [signedIn, setSignedIn] = useState<boolean | null>(null)
  const [title, setTitle] = useState('')
  const [amountMinor, setAmountMinor] = useState<number | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void hasSignedInIdToken().then((ok) => {
      if (!cancelled) setSignedIn(ok)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!checkoutParams) return
    let cancelled = false
    setLoadError(null)
    setTitle('')
    setAmountMinor(null)

    void (async () => {
      try {
        if (checkoutParams.productType === 'bundle') {
          const offer = await getBundle()
          if (cancelled) return
          setTitle('Research Mastery Bundle')
          setAmountMinor(offer.amountMinor)
          return
        }
        const course = await getCourse(checkoutParams.courseId)
        if (cancelled) return
        setTitle(course.title)
        if (typeof course.amountMinor === 'number' && course.amountMinor > 0) {
          setAmountMinor(course.amountMinor)
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(catalogApiUserMessage(err, 'loadCourse'))
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [checkoutParams])

  const onSignIn = useCallback(() => {
    persistReturnPathBeforeHostedUi()
    navigate('/login')
  }, [navigate])

  const onSubmit = useCallback(async () => {
    if (!checkoutParams || signedIn !== true) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const body =
        checkoutParams.productType === 'bundle'
          ? { productType: 'bundle' as CheckoutProductType }
          : {
              productType: 'course' as CheckoutProductType,
              courseId: checkoutParams.courseId,
            }
      const { redirect_url } = await createCheckoutSession(body)
      if (!isHttpsUrl(redirect_url)) {
        setSubmitError(catalogApiUserMessage(new Error('invalid redirect'), 'checkout'))
        return
      }
      window.location.href = redirect_url
    } catch (err) {
      setSubmitError(catalogApiUserMessage(err, 'checkout'))
    } finally {
      setSubmitting(false)
    }
  }, [checkoutParams, signedIn])

  if (!checkoutParams) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-rs-ink">
        <h1 className="text-2xl font-extrabold tracking-tight">Checkout</h1>
        <p className="mt-3 text-sm text-rs-body">This checkout link is invalid. Choose a course or bundle from the catalog.</p>
        <Button to="/courses" className="mt-6">
          Browse courses
        </Button>
      </div>
    )
  }

  const priceLabel = amountMinor != null ? formatUsdMinor(amountMinor) : null

  return (
    <div className="mx-auto max-w-lg px-4 py-16 text-rs-ink" data-testid="checkout-page">
      <h1 className="text-2xl font-extrabold tracking-tight">Checkout</h1>
      <p className="mt-2 text-sm text-rs-body">Review your order, then continue to secure payment.</p>

      <section className="mt-8 rounded-2xl border border-rs-line bg-white p-6 shadow-rs-sm" aria-label="Order summary">
        <h2 className="text-sm font-extrabold uppercase tracking-wider text-rs-muted">Order summary</h2>
        {loadError ? (
          <p className="mt-4 text-sm text-red-700" role="alert">
            {loadError}
          </p>
        ) : (
          <>
            <p className="mt-4 text-lg font-bold text-rs-ink">{title || 'Loading…'}</p>
            <p className="mt-1 text-sm text-rs-body">
              {checkoutParams.productType === 'bundle' ? 'All published courses — lifetime access' : 'One course — lifetime access'}
            </p>
            {priceLabel ? (
              <p className="mt-4 text-2xl font-extrabold text-rs-blue">{priceLabel}</p>
            ) : null}
          </>
        )}
      </section>

      {signedIn === false ? (
        <div className="mt-6 rounded-2xl border border-rs-line bg-rs-sky-2/40 p-5">
          <p className="text-sm text-rs-body">Sign in to link this purchase to your account before payment.</p>
          <Button type="button" className="mt-4 w-full" onClick={onSignIn}>
            Sign in to continue
          </Button>
        </div>
      ) : null}

      {signedIn === true ? (
        <div className="mt-6 space-y-3">
          <Button
            type="button"
            className="w-full"
            disabled={submitting || Boolean(loadError)}
            onClick={() => void onSubmit()}
            data-testid="checkout-submit"
          >
            {submitting ? checkoutLoadingLabel : 'Continue to payment'}
          </Button>
          {submitError ? (
            <p className="text-sm text-red-700" role="alert">
              {submitError}
            </p>
          ) : null}
        </div>
      ) : null}

      <p className="mt-8 text-center text-sm text-rs-muted">
        <Link to="/courses" className="font-semibold text-rs-blue no-underline hover:opacity-90">
          Back to catalog
        </Link>
      </p>
    </div>
  )
}
