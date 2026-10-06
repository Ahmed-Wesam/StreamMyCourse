import { useCallback, useEffect, useState } from 'react'

import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Field } from '../components/ui/Field'
import { getBundle } from '../lib/api/billing'
import { setBundlePrice } from '../lib/api/pricing'
import { ApiError } from '../lib/api/client'
import { BRAND_NAME } from '../lib/brand'
import { jodMinorToInputValue, parseJodInputToMinor } from '../lib/jodPriceInput'
import { privacyUrl, termsUrl } from '../lib/legalUrls'
import { usePageTitle } from '../lib/page-title'

function bundlePriceUserMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403 || err.code === 'forbidden') {
      return 'Only the designated billing teacher can change the bundle price.'
    }
    if (err.code === 'invalid_amount') {
      return 'Enter a positive whole-number JOD amount (for example 150).'
    }
    if (err.message.trim()) return err.message.trim()
  }
  if (err instanceof Error && err.message.trim()) return err.message.trim()
  return 'The bundle price could not be saved. Please try again.'
}

export default function TeacherPaymentSetup() {
  usePageTitle('Pricing')

  const [bundlePriceJod, setBundlePriceJod] = useState('')
  const [bundleLoading, setBundleLoading] = useState(true)
  const [bundleSaving, setBundleSaving] = useState(false)
  const [bundleError, setBundleError] = useState<string | null>(null)

  const loadBundleOffer = useCallback(async () => {
    try {
      setBundleLoading(true)
      setBundleError(null)
      const offer = await getBundle()
      setBundlePriceJod(jodMinorToInputValue(offer.amountMinor))
    } catch (err) {
      setBundlePriceJod('')
      setBundleError(
        err instanceof ApiError && err.code === 'bundle_not_configured'
          ? 'Bundle pricing is not configured yet. Contact the platform operator.'
          : bundlePriceUserMessage(err),
      )
    } finally {
      setBundleLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadBundleOffer()
  }, [loadBundleOffer])

  const handleSaveBundlePrice = async () => {
    const amountMinor = parseJodInputToMinor(bundlePriceJod)
    if (amountMinor == null) {
      setBundleError('Enter a positive whole-number JOD amount (for example 150).')
      return
    }

    setBundleSaving(true)
    setBundleError(null)
    try {
      const offer = await setBundlePrice(amountMinor)
      setBundlePriceJod(jodMinorToInputValue(offer.amountMinor))
    } catch (err) {
      setBundleError(bundlePriceUserMessage(err))
    } finally {
      setBundleSaving(false)
    }
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-8 text-rs-ink sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold tracking-tight text-rs-navy">Pricing</h1>
        <p className="mt-2 text-sm text-rs-body">
          Students buy individual courses or the all-access bundle through secure HyperPay checkout
          on {BRAND_NAME}. Card processing is handled by HyperPay; platform operators configure
          merchant credentials in AWS.
        </p>
      </div>

      <Card className="p-4">
        <h2 className="text-sm font-extrabold text-rs-navy">All-access bundle price</h2>
        <p className="mt-2 text-sm text-rs-body">
          Set the one-time JOD price students pay for the full course catalog bundle (whole dinars
          only).
        </p>
        {bundleLoading ? (
          <p className="mt-3 text-sm text-rs-body" role="status">
            Loading bundle price…
          </p>
        ) : (
          <>
            <Field
              label="Bundle price (JOD)"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              autoComplete="off"
              className="mt-3"
              value={bundlePriceJod}
              error={bundleError ?? undefined}
              onChange={(e) => {
                setBundlePriceJod(e.target.value.replace(/[^\d]/g, ''))
                if (bundleError) setBundleError(null)
              }}
            />
            <Button
              type="button"
              size="sm"
              className="mt-1"
              disabled={bundleSaving}
              onClick={() => void handleSaveBundlePrice()}
            >
              {bundleSaving ? 'Saving…' : 'Save bundle price'}
            </Button>
          </>
        )}
      </Card>

      <Card className="mt-6 p-4">
        <h2 className="text-sm font-extrabold text-rs-navy">HyperPay merchant profile URLs</h2>
        <p className="mt-2 text-sm text-rs-body">
          Copy these absolute links into the HyperPay merchant portal (terms and privacy fields).
        </p>
        <dl className="mt-4 space-y-3 text-sm">
          <div>
            <dt className="font-semibold text-rs-navy">Terms</dt>
            <dd className="mt-1 break-all font-mono text-xs text-rs-body">{termsUrl()}</dd>
          </div>
          <div>
            <dt className="font-semibold text-rs-navy">Privacy</dt>
            <dd className="mt-1 break-all font-mono text-xs text-rs-body">{privacyUrl()}</dd>
          </div>
        </dl>
      </Card>
    </main>
  )
}
